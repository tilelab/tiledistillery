"""The `tiledistillery` command; each step parses, then hands off."""
import argparse
import importlib.metadata
import os
import subprocess
import sys
from collections.abc import Sequence

from tiledistillery.layers import Layer, parse_layers
from tiledistillery.layout import EXTRACTS_DIR, PARTS_DIR, PLAN_DIR
from tiledistillery.merge import merge_layer
from tiledistillery.plan import plan_run
from tiledistillery.sources import DEFAULT_SOURCE, load_source
from tiledistillery.sources.base import Source
from tiledistillery.work import DEFAULT_TILEMAKER_IMAGE, build_shard

HELP: str = """Builds vector-tile layers from OSM extracts with tilemaker, in
steps that may run on different machines beside the same plan/: `plan` once,
`work` once per shard, `merge` once per layer.

See https://github.com/tilelab/tiledistillery/blob/main/docs/reference/cli.md.
"""

PLAN_HELP: str = """Plans the run, once, before any worker starts.

Asks --source for its regions and splits those in scope into --shards
shards of about equal .osm.pbf bytes. Writes plan/plan.json, which every
later step reads. Paths are relative to the working directory, the only one
tilemaker sees.

    tiledistillery plan --config tiles/config.json \
        --process tiles/process.lua --layer bins \
        --attribution "(c) OpenStreetMap contributors, ODbL" --shards 20
"""

WORK_HELP: str = """Builds one shard.

Downloads each of its regions once and runs tilemaker in Docker for every
layer. Writes parts/N/, replacing it.

    tiledistillery work --shard 0
"""

MERGE_HELP: str = """Merges one layer, after every shard is built.

Joins the layer's tiles from parts/*/ with tile-join, from tippecanoe, into
layers/<layer>.pmtiles. Fails if a shard is missing.

    tiledistillery merge --layer bins
"""

DEFAULT_SHARDS: int = 1


def _count(value: str, flag: str) -> int:
    """Returns a positive integer flag value.

    Raises:
        ValueError: If it isn't one.
    """
    if not value.isdigit() or int(value) < 1:
        raise ValueError(f"{flag} must be a positive integer, not {value!r}")
    return int(value)


def _plan(args: argparse.Namespace) -> None:
    """Plans the run, checking every value first."""
    plan_parser: argparse.ArgumentParser = args.parser
    leftover: list[str] = [path for path in (PLAN_DIR, EXTRACTS_DIR, PARTS_DIR)
                           if os.path.exists(path)]
    if leftover:
        plan_parser.error(f"the working directory holds {', '.join(leftover)} "
                          f"from another run; delete "
                          f"{'it' if len(leftover) == 1 else 'them'} first")
    layers: list[Layer]
    source: Source
    shard_count: int
    try:
        layers = parse_layers(args.config, args.process, args.layer)
        if not args.attribution:
            raise ValueError("--attribution is required, as OSM data needs it")
        source = load_source(args.source or DEFAULT_SOURCE)
        shard_count = (_count(args.shards, "--shards") if args.shards
                       else DEFAULT_SHARDS)
    except ValueError as error:
        plan_parser.error(str(error))
    plan_run(layers, args.attribution, source,
             [prefix.strip() for prefix in (args.regions or "").split(",")
              if prefix.strip()],
             shard_count)


def _work(args: argparse.Namespace) -> None:
    """Builds one shard."""
    build_shard(args.shard, args.tilemaker_image or DEFAULT_TILEMAKER_IMAGE)


def _merge(args: argparse.Namespace) -> None:
    """Merges one layer."""
    merge_layer(args.layer)


def parser() -> argparse.ArgumentParser:
    """Returns the command's parser with every step.

    An empty option value counts as not given, for orchestrators that
    pass every input.
    """
    top: argparse.ArgumentParser = argparse.ArgumentParser(
        prog="tiledistillery", description=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    top.add_argument(
        "--version", action="version",
        version=f"%(prog)s {importlib.metadata.version('tiledistillery')}")
    steps: "argparse._SubParsersAction[argparse.ArgumentParser]" = (
        top.add_subparsers(title="steps", metavar="STEP", dest="step",
                           required=True))

    plan: argparse.ArgumentParser = steps.add_parser(
        "plan", help="split the regions in scope into shards",
        description=PLAN_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    plan.add_argument(
        "--config", required=True,
        help="tilemaker's JSON config, or a comma-separated list, one per "
             "layer")
    plan.add_argument(
        "--process", required=True,
        help="tilemaker's Lua process script, or a list like --config")
    plan.add_argument(
        "--layer", required=True,
        help="the layer's name, or a list like --config, such as bins,roads")
    plan.add_argument(
        "--attribution", required=True,
        help="written into every layer's metadata")
    plan.add_argument(
        "--source",
        help=f"the installed source of the regions (default "
             f"{DEFAULT_SOURCE})")
    plan.add_argument(
        "--regions",
        help="comma-separated region ids, each with every region below it, "
             "such as europe or europe/monaco,europe/andorra (default: all)")
    plan.add_argument(
        "--shards",
        help=f"how many shards to split the run into (default "
             f"{DEFAULT_SHARDS})")
    plan.set_defaults(run=_plan, parser=plan)

    work: argparse.ArgumentParser = steps.add_parser(
        "work", help="build one shard's regions", description=WORK_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    work.add_argument(
        "--shard", type=int, required=True,
        help="which of the plan's shards to build, counted from 0")
    work.add_argument(
        "--tilemaker-image",
        help=f"the tilemaker Docker image (default {DEFAULT_TILEMAKER_IMAGE})")
    work.set_defaults(run=_work)

    merge: argparse.ArgumentParser = steps.add_parser(
        "merge", help="join one layer's tiles into the layer",
        description=MERGE_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    merge.add_argument(
        "--layer", required=True,
        help="which of the plan's layers to merge, by name")
    merge.set_defaults(run=_merge)
    return top


def main(argv: Sequence[str] | None = None) -> None:
    """Runs the command with `argv`, or the command line's arguments."""
    args: argparse.Namespace = parser().parse_args(argv)
    if sys.platform == "win32":
        # work's Docker call and paths are POSIX-only, and tile-join has no
        # Windows build; refused before a download is wasted.
        sys.exit(f"tiledistillery {args.step}: Windows is not supported; run "
                 f"tiledistillery in WSL")
    try:
        args.run(args)
    except (OSError, RuntimeError, ValueError,
            subprocess.CalledProcessError) as error:
        # The message, or the tool's output above it, says what went wrong.
        sys.exit(f"tiledistillery {args.step}: {error}")
