"""Installed sources, found through entry points.

See docs/reference/sources.md.
"""
from importlib.metadata import EntryPoint, entry_points

from tiledistillery.sources.base import Source

SOURCE_GROUP: str = "tiledistillery.sources"
DEFAULT_SOURCE: str = "geofabrik"


def load_source(name: str) -> Source:
    """Returns the Source installed as `name`.

    Raises:
        ValueError: If no such source is installed.
    """
    found: dict[str, EntryPoint] = {
        entry_point.name: entry_point
        for entry_point in entry_points(group=SOURCE_GROUP)}
    if name not in found:
        raise ValueError(f"no source named {name!r} is installed (installed: "
                         f"{', '.join(sorted(found)) or 'none'})")
    source_class: type[Source] = found[name].load()
    return source_class()
