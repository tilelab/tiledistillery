"""Geofabrik's leaf extracts, the finest along each branch of its tree."""
from typing import Any, TypeAlias

import requests

from tiledistillery import log
from tiledistillery.sources.base import Region, Source

INDEX_URL: str = "https://download.geofabrik.de/index-v1.json"

# Leaves that finer extracts cover, which index-v1.json doesn't mark:
# - the "Special Sub Regions" each continent's download page lists, such as
#   download.geofabrik.de/europe.html#specialsubregions (checked
#   2026-08-20);
# - `us`, whose states name `north-america` as their parent;
# - `enfield`, the only London borough with its own extract, which must not
#   make `greater-london` a parent (see _leaves()).
KNOWN_REDUNDANT_LEAVES: frozenset[str] = frozenset({
    "us", "us-midwest", "us-northeast", "us-pacific", "us-south", "us-west",
    "alps", "britain-and-ireland", "dach", "great-britain",
    "south-africa-and-lesotho", "sea", "kaliningrad",
    "enfield",
})

Feature: TypeAlias = dict[str, Any]


def _paths(features: list[Feature]) -> dict[str, str]:
    """Returns each Geofabrik id's path through its parents."""
    parents: dict[str, str | None] = {
        feature["properties"]["id"]: feature["properties"].get("parent")
        for feature in features
    }
    paths: dict[str, str] = {}

    def path_of(geofabrik_id: str) -> str:
        if geofabrik_id not in paths:
            parent: str | None = parents[geofabrik_id]
            paths[geofabrik_id] = (f"{path_of(parent)}/{geofabrik_id}"
                                   if parent else geofabrik_id)
        return paths[geofabrik_id]

    geofabrik_id: str
    for geofabrik_id in parents:
        path_of(geofabrik_id)
    return paths


def _leaves(features: list[Feature]) -> list[Feature]:
    """Returns the features no other one names as its parent."""
    # A redundant leaf's parent stays a leaf, or excluding `enfield` would
    # drop the rest of London too.
    parents: set[str | None] = {
        feature["properties"].get("parent") for feature in features
        if feature["properties"]["id"] not in KNOWN_REDUNDANT_LEAVES
    }
    return [
        feature for feature in features
        if feature["properties"]["id"] not in parents
        and feature["properties"]["id"] not in KNOWN_REDUNDANT_LEAVES
    ]


class GeofabrikSource(Source):
    """Every leaf of download.geofabrik.de, named by its path, such as
    `europe/germany/bavaria`, so that `--regions` can pick subtrees.

    Regions are never split or joined, so Russia and Vatican City are one
    region each.
    """

    def regions(self) -> list[Region]:
        response: requests.Response = requests.get(INDEX_URL, timeout=60)
        response.raise_for_status()
        features: list[Feature] = response.json()["features"]
        paths: dict[str, str] = _paths(features)
        regions: list[Region] = []
        feature: Feature
        for feature in _leaves(features):
            path: str = paths[feature["properties"]["id"]]
            url: str | None = feature["properties"].get("urls", {}).get("pbf")
            if url:
                regions.append(Region(path, url))
            else:
                log.warning("Region skipped",
                            f"{path}: Geofabrik's index has no .osm.pbf URL")
        return regions
