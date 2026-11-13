"""Merging one layer's region tiles from every shard with `tile-join`."""
import glob
import json
import os
import shutil
import subprocess
from typing import Any, TextIO

from tiledistillery import log
from tiledistillery.layout import (
    LAYERS_DIR,
    OUTCOMES_FILENAME,
    PARTS_DIR,
    layer_path,
    outcomes_path,
)
from tiledistillery.plan import RunPlan, read_plan
from tiledistillery.redraws import run_throttled
from tiledistillery.sources.base import Region

_TILE_JOIN_INTERVAL: float = 60


def _outcomes() -> dict[str, str | None]:
    """Returns every shard's outcomes: per region id, why it failed or None."""
    outcomes: dict[str, str | None] = {}
    path: str
    for path in glob.glob(os.path.join(PARTS_DIR, "*", OUTCOMES_FILENAME)):
        outcomes_file: TextIO
        with open(path, encoding="utf-8") as outcomes_file:
            line: str
            for line in outcomes_file:
                outcome: dict[str, Any] = json.loads(line)
                outcomes[outcome["region_id"]] = outcome["error"]
    return outcomes


def _check_complete(plan: RunPlan, outcomes: dict[str, str | None]) -> None:
    """Raises RuntimeError naming the shards with unbuilt regions."""
    unfinished: list[str] = []
    index: int
    shard: list[Region]
    for index, shard in enumerate(plan.shards):
        missing: int = sum(region.id not in outcomes for region in shard)
        if missing:
            unfinished.append(f"shard {index} ({outcomes_path(index)} lacks "
                              f"{missing} of {len(shard)} region(s))")
    if unfinished:
        raise RuntimeError(f"not every shard is built: {'; '.join(unfinished)}"
                           f"; run `tiledistillery work` for each")


def merge_layer(layer: str) -> None:
    """Joins a layer's region tiles into `layers/<layer>.pmtiles`.

    Raises:
        ValueError: If the plan builds no such layer.
        RuntimeError: If a shard isn't built, the layer has no tiles, or
            tile-join is missing.
        subprocess.CalledProcessError: If tile-join fails.
    """
    plan: RunPlan = read_plan()
    names: list[str] = [planned.name for planned in plan.layers]
    if layer not in names:
        raise ValueError(f"{layer}: the plan builds no such layer, only "
                         f"{', '.join(names)}")
    outcomes: dict[str, str | None] = _outcomes()
    _check_complete(plan, outcomes)
    failed: list[str] = sorted(region_id for region_id, error
                               in outcomes.items() if error is not None)
    if failed:
        log.warning("Regions missing",
                    f"{layer} lacks {len(failed)} failed region(s): "
                    f"{', '.join(failed)}")
    tiles: list[str] = sorted(
        glob.glob(os.path.join(PARTS_DIR, "*", layer, "*.pmtiles")))
    if not tiles:
        raise RuntimeError(f"{layer}: no region was built")
    if shutil.which("tile-join") is None:
        raise RuntimeError("tile-join is not on PATH; install tippecanoe "
                           "with `brew install tippecanoe` or `apt install "
                           "tippecanoe`, or build it from "
                           "https://github.com/felt/tippecanoe")
    os.makedirs(LAYERS_DIR, exist_ok=True)
    command: list[str] = [
        "tile-join", "--no-tile-size-limit", "--force",
        f"--attribution={plan.attribution}", "-o", layer_path(layer), *tiles]
    status: int = run_throttled(command, _TILE_JOIN_INTERVAL)
    if status:
        raise subprocess.CalledProcessError(status, command[0])
    log.info(f"merged {len(tiles)} region(s) into {layer_path(layer)}, "
             f"{os.path.getsize(layer_path(layer)) / 1e6:.1f} MB")
