"""Building one shard: each region downloaded once, then every layer's tiles.

A failed region is not retried: curl already retries transient errors, and a
broken extract would only fail again. It is a warning, and no layer gets any
of it.
"""
import json
import os
import re
import shutil
import time
from typing import TextIO

from tiledistillery import log
from tiledistillery.layers import Layer
from tiledistillery.layout import (
    extract_path,
    outcomes_path,
    part_dir,
    region_tiles_path,
    store_dir,
)
from tiledistillery.plan import RunPlan, read_plan
from tiledistillery.redraws import run_throttled
from tiledistillery.sources.base import Region

# The only tag upstream publishes.
DEFAULT_TILEMAKER_IMAGE: str = "ghcr.io/systemed/tilemaker:master"

# Seconds between progress lines; a stalled download shows up sooner.
_DOWNLOAD_INTERVAL: float = 15
_TILEMAKER_INTERVAL: float = 60
# The image's entrypoint prints this banner before every build.
_TILEMAKER_BANNER: re.Pattern[bytes] = re.compile(
    rb"-{80}"
    rb"|DOCKER WARNING: Docker Out Of Memory handling can be unreliable\."
    rb"|DOCKER WARNING: If your program unexpectedly exits, it might have "
    rb"been terminated by the Out Of Memory killer without a visible "
    rb"notice\."
    rb"|DOCKER WARNING: The --store option can be used to partly reduce "
    rb"memory usage\."
)


def _download(url: str, path: str) -> int:
    """Returns curl's exit code after downloading `url` to `path`."""
    # --retry covers timeouts, 5xx, 408 and 429 but not a 404. Geofabrik
    # outages have lasted 15 minutes, hence --retry-max-time.
    return run_throttled(
        ["curl", "-fL", "--retry", "20", "--retry-max-time", "1200",
         "--retry-connrefused", url, "-o", path],
        _DOWNLOAD_INTERVAL)


def _tilemaker(layer: Layer, shard_index: int, region: Region,
               image: str) -> int:
    """Returns tilemaker's exit code after building one region's tiles.

    The container runs in the working directory, mounted as /data, so every
    path is relative to it.
    """
    store: str = store_dir(shard_index)
    os.makedirs(store)
    try:
        return run_throttled(
            ["docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}",
             "-v", f"{os.getcwd()}:/data", "-w", "/data", image,
             "--input", extract_path(shard_index),
             "--output", region_tiles_path(shard_index, layer.name, region.id),
             "--config", layer.config, "--process", layer.process,
             # On disk for every region, so memory doesn't depend on size.
             "--store", store],
            _TILEMAKER_INTERVAL, _TILEMAKER_BANNER)
    finally:
        shutil.rmtree(store, ignore_errors=True)


def _build_region(plan: RunPlan, shard_index: int, region: Region,
                  image: str) -> str | None:
    """Returns why the region failed, or None once every layer is built."""
    extract: str = extract_path(shard_index)
    log.info(f"downloading {region.url}")
    error: str | None = None
    status: int = _download(region.url, extract)
    if status:
        error = f"download failed (curl exit {status})"
    layer: Layer
    for layer in [] if error else plan.layers:
        status = _tilemaker(layer, shard_index, region, image)
        if status:
            error = f"{layer.name}: tilemaker failed (exit {status})"
            break
    if os.path.exists(extract):
        os.remove(extract)
    if error is not None:
        # Then no layer gets part of the region.
        for layer in plan.layers:
            tiles: str = region_tiles_path(shard_index, layer.name, region.id)
            if os.path.exists(tiles):
                os.remove(tiles)
    return error


def build_shard(shard_index: int, image: str) -> None:
    """Builds every region of a shard into `parts/N/`, replacing it.

    Raises:
        ValueError: If the plan has no such shard.
    """
    plan: RunPlan = read_plan()
    if not 0 <= shard_index < len(plan.shards):
        raise ValueError(f"shard {shard_index}: plan has shards 0 to "
                         f"{len(plan.shards) - 1}")
    shutil.rmtree(part_dir(shard_index), ignore_errors=True)
    layer: Layer
    for layer in plan.layers:
        os.makedirs(os.path.join(part_dir(shard_index), layer.name))
    os.makedirs(os.path.dirname(extract_path(shard_index)), exist_ok=True)
    failed: int = 0
    region: Region
    for region in plan.shards[shard_index]:
        start: float = time.monotonic()
        error: str | None
        with log.group(region.id):
            error = _build_region(plan, shard_index, region, image)
            log.info(f"{'failed' if error else 'built'} in "
                     f"{time.monotonic() - start:.0f} s")
        if error is not None:
            failed += 1
            log.warning("Region failed", f"{region.id}: {error}")
        outcomes: TextIO
        with open(outcomes_path(shard_index), "a",
                  encoding="utf-8") as outcomes:
            outcomes.write(json.dumps({"region_id": region.id, "error": error})
                           + "\n")
    log.info(f"shard {shard_index}: {len(plan.shards[shard_index]) - failed} "
             f"region(s) built, {failed} failed")
