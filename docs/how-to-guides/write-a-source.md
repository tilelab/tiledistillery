# Write a source

A source tells `plan` which extracts there are. Write one to build from
extracts Geofabrik doesn't have, such as your own cuts of a planet file.

## Step 1: Write the source

Subclass `Source` and return the regions from `regions()`:

```python
# my_source.py
from tiledistillery.sources.base import Region, Source


class MirrorSource(Source):
    def regions(self) -> list[Region]:
        return [
            Region("alps/east", "https://extracts.example.org/alps-east.osm.pbf"),
            Region("alps/west", "https://extracts.example.org/alps-west.osm.pbf"),
        ]
```

With these ids, `--regions alps` selects both, and
`--regions alps/east` one.

## Step 2: Declare the entry point

```toml
# pyproject.toml
[project]
name = "my-source"
version = "1.0.0"
dependencies = ["tiledistillery"]

[project.entry-points."tiledistillery.sources"]
mirror = "my_source:MirrorSource"
```

## Step 3: Use it

Install the package beside tiledistillery where `plan` runs; the other
steps read the regions from `plan/`:

```sh
pip install ./my-source
tiledistillery plan --source mirror --config ...
```

`_pipeline.yml` has no source input, so it always uses Geofabrik.
