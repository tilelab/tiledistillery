"""The Source contract: which extracts a run can build."""
from abc import ABC, abstractmethod
from typing import NamedTuple


class Region(NamedTuple):
    """An extract, built on its own.

    Attributes:
        id: Unique and `/`-separated, such as `europe/germany/bavaria`;
            `plan --regions` selects regions by its leading parts.
        url: The extract's `.osm.pbf`.
    """

    id: str
    url: str


class Source(ABC):
    """A provider of OSM extracts, installed as an entry point.

    See docs/reference/sources.md. `__init__` gets no arguments.
    """

    @abstractmethod
    def regions(self) -> list[Region]:
        """Returns every region; called once, by `plan`.

        Regions must not overlap, or a layer gets the shared features twice.
        """
