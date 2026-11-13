"""`plan/plan.json`, and splitting the regions in scope into shards.

Each shard gets about the same `.osm.pbf` bytes, the best predictor of a
region's build time there is; see docs/explanation/architecture.md.
"""
import concurrent.futures
import dataclasses
import heapq
import importlib.metadata
import json
import os
from typing import Any, Self, TextIO

import requests
import requests.adapters
import urllib3.util

from tiledistillery import log
from tiledistillery.layers import Layer
from tiledistillery.layout import PLAN_DIR, PLAN_PATH
from tiledistillery.sources.base import Region, Source

# The tiledistillery that writes and reads plan.json. Its key never
# changes, so every version can tell that another wrote a plan/.
VERSION: str = importlib.metadata.version("tiledistillery")

# Parallel HEAD requests for the sizes; hundreds on a world run.
_SIZE_THREADS: int = 16


@dataclasses.dataclass(frozen=True)
class RunPlan:
    """What every step after `plan` needs.

    Attributes:
        attribution: Written into every layer's metadata.
        layers: The layers, one merge each, in `--layer`'s order.
        shards: Each shard's regions, largest first.
    """

    attribution: str
    layers: list[Layer]
    shards: list[list[Region]]

    def as_json(self) -> dict[str, Any]:
        """Returns the plan as plan.json holds it."""
        return {
            "version": VERSION,
            "attribution": self.attribution,
            "layers": [dataclasses.asdict(layer) for layer in self.layers],
            "shards": [[region._asdict() for region in shard]
                       for shard in self.shards],
        }

    @classmethod
    def from_json(cls, document: dict[str, Any]) -> Self:
        """Returns the plan `as_json()` wrote.

        Raises:
            ValueError: If another tiledistillery version wrote it.
        """
        version: Any = document.get("version")
        if version != VERSION:
            raise ValueError(f"tiledistillery {version} wrote {PLAN_PATH}, "
                             f"but this is {VERSION}; run every step of a "
                             f"run with the same tiledistillery")
        return cls(
            attribution=document["attribution"],
            layers=[Layer(**layer) for layer in document["layers"]],
            shards=[[Region(**region) for region in shard]
                    for shard in document["shards"]],
        )


def read_plan() -> RunPlan:
    """Returns the plan in `plan/plan.json`.

    Raises:
        OSError: If the file cannot be read.
        KeyError: If a key is missing.
        ValueError: If it is not JSON, or another tiledistillery version
            wrote it.
    """
    plan_file: TextIO
    with open(PLAN_PATH, encoding="utf-8") as plan_file:
        return RunPlan.from_json(json.load(plan_file))


def in_scope(region_id: str, prefixes: list[str]) -> bool:
    """Returns whether a region is one of `prefixes` or below one."""
    return not prefixes or any(
        region_id == prefix or region_id.startswith(prefix + "/")
        for prefix in prefixes)


def _sizes(regions: list[Region]) -> list[int]:
    """Returns each region's `.osm.pbf` size, by HEAD request."""
    session: requests.Session = requests.Session()
    # Hundreds of requests on every run, so transient errors get retried.
    session.mount("https://", requests.adapters.HTTPAdapter(
        max_retries=urllib3.util.Retry(total=5, backoff_factor=1,
                                       status_forcelist=[429, 500, 502, 503,
                                                         504])))

    def size(region: Region) -> int:
        response: requests.Response = session.head(
            region.url, timeout=30, allow_redirects=True)
        response.raise_for_status()
        return int(response.headers.get("Content-Length", 0))

    pool: concurrent.futures.ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(_SIZE_THREADS) as pool:
        return list(pool.map(size, regions))


def split(regions: list[Region], sizes: list[int],
          shard_count: int) -> list[list[Region]]:
    """Returns the regions in `shard_count` shards of about equal bytes.

    Largest first, each region goes to the shard with the fewest bytes so
    far, which keeps a large region from landing last on a full shard.
    """
    shards: list[list[Region]] = [[] for _ in range(shard_count)]
    loads: list[tuple[int, int]] = [(0, index) for index in range(shard_count)]
    region: Region
    size: int
    for size, region in sorted(zip(sizes, regions),
                               key=lambda pair: -pair[0]):
        load: int
        index: int
        load, index = heapq.heappop(loads)
        shards[index].append(region)
        heapq.heappush(loads, (load + size, index))
    return shards


def plan_run(layers: list[Layer], attribution: str, source: Source,
             prefixes: list[str], shard_count: int) -> None:
    """Writes `plan/` for the layers of the regions in scope.

    Raises:
        ValueError: If a prefix matches no region, or there are none.
    """
    regions: list[Region] = [region for region in source.regions()
                             if in_scope(region.id, prefixes)]
    prefix: str
    for prefix in prefixes:
        if not any(in_scope(region.id, [prefix]) for region in regions):
            raise ValueError(f"--regions: {prefix!r} matches no region")
    if not regions:
        raise ValueError("the source has no regions")
    sizes: list[int] = _sizes(regions)
    plan: RunPlan = RunPlan(attribution, layers,
                            split(regions, sizes, min(shard_count,
                                                      len(regions))))
    os.makedirs(PLAN_DIR)
    plan_file: TextIO
    with open(PLAN_PATH, "w", encoding="utf-8") as plan_file:
        json.dump(plan.as_json(), plan_file, indent=1)
    log.info(f"planned {len(regions)} region(s), {sum(sizes) / 1e6:,.0f} MB, "
             f"in {len(plan.shards)} shard(s) for "
             f"{', '.join(layer.name for layer in layers)}")
