"""Every path the steps read and write, relative to the working directory.

See docs/reference/cli.md "Run directory".
"""
import os

PLAN_DIR: str = "plan"
EXTRACTS_DIR: str = "extracts"
PARTS_DIR: str = "parts"
LAYERS_DIR: str = "layers"

PLAN_PATH: str = os.path.join(PLAN_DIR, "plan.json")

OUTCOMES_FILENAME: str = "outcomes.jsonl"


def extract_path(shard_index: int) -> str:
    """Returns `extracts/N.osm.pbf`."""
    return os.path.join(EXTRACTS_DIR, f"{shard_index}.osm.pbf")


def store_dir(shard_index: int) -> str:
    """Returns `extracts/N.store`."""
    return os.path.join(EXTRACTS_DIR, f"{shard_index}.store")


def part_dir(shard_index: int) -> str:
    """Returns `parts/N`."""
    return os.path.join(PARTS_DIR, str(shard_index))


def outcomes_path(shard_index: int) -> str:
    """Returns `parts/N/outcomes.jsonl`."""
    return os.path.join(part_dir(shard_index), OUTCOMES_FILENAME)


def region_tiles_path(shard_index: int, layer: str, region_id: str) -> str:
    """Returns `parts/N/<layer>/<region>.pmtiles`, `/` in the id as `_`."""
    # PMTiles, not MBTiles: without SQLite's overhead a shard's artifact is
    # smaller, and tile-join reads either.
    return os.path.join(part_dir(shard_index), layer,
                        region_id.replace("/", "_") + ".pmtiles")


def layer_path(layer: str) -> str:
    """Returns `layers/<layer>.pmtiles`."""
    return os.path.join(LAYERS_DIR, f"{layer}.pmtiles")
