# Sources reference

A **source** lists the regions a run can build. `plan` picks it with
`--source`.

| Source | Regions |
| --- | --- |
| `geofabrik` (default) | Every leaf of [Geofabrik's](https://download.geofabrik.de) tree, the finest extract along each branch, named by its path, such as `europe/germany/bavaria`. |

## Source

`tiledistillery.sources.base.Source`, installed as an entry point in the
`tiledistillery.sources` group; see
[Write a source](../how-to-guides/write-a-source.md). Its constructor takes
no arguments.

| Member | Description |
| --- | --- |
| `regions()` | Required. Returns every region as a `Region`. `plan` calls it once per run. |

## Region

`tiledistillery.sources.base.Region`, a named tuple.

| Field | Description |
| --- | --- |
| `id` | Unique and `/`-separated; `--regions` selects by its leading parts. |
| `url` | The extract's `.osm.pbf`. `plan` takes its size from a `HEAD` request's `Content-Length`; without one, it counts as empty. |

Regions must not overlap, or a layer gets the shared features twice.
