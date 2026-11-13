# tiledistillery

tiledistillery builds PMTiles vector-tile layers of the world, or part of
it, from [Geofabrik](https://download.geofabrik.de) OSM extracts with
[tilemaker](https://github.com/systemed/tilemaker). You bring the tilemaker
JSON config and Lua process script; tiledistillery spreads the extracts over
many workers and merges each layer into one `.pmtiles`.

It runs anywhere that can run its three steps, and comes with reusable
GitHub Actions workflows. It is a sibling of
[tilealchemist](https://github.com/tilelab/tilealchemist), which builds
layers from a PMTiles archive instead; neither uses the other.

## Getting started

New here?
[Build your first layer](https://github.com/tilelab/tiledistillery/blob/main/docs/tutorials/build-your-first-layer.md)
walks through both ways.

### On GitHub Actions

```yaml
name: Build my layer

on:
  workflow_dispatch:
  schedule:
    - cron: "0 3 * * 0"

jobs:
  build:
    uses: tilelab/tiledistillery/.github/workflows/_pipeline.yml@v1.0.0
    permissions:
      contents: read
    with:
      config: tiles/config.json
      process: tiles/process.lua
      layer: my-layer
      attribution: "My Layer, data (c) OpenStreetMap contributors, ODbL"
      # regions: europe/germany

  publish:
    needs: build
    uses: tilelab/tiledistillery/.github/workflows/_publish-release.yml@v1.0.0
    permissions:
      contents: write
    with:
      layer: my-layer
      tag: my-layer-latest
      title: "My Layer"
```

The layer comes back as the artifact `my-layer-pmtiles`; the `publish` job
is optional.
[ci.yml](https://github.com/tilelab/tiledistillery/blob/main/.github/workflows/ci.yml)
builds two layers from one download.

### Anywhere else

On macOS or Linux, or on Windows in WSL, with Python 3.11 or newer, Docker
and [tippecanoe](https://github.com/felt/tippecanoe)'s `tile-join`
(`brew install tippecanoe`, `apt install tippecanoe` or
[built from source](https://github.com/felt/tippecanoe#installation)), in the
directory holding `tiles/`:

```sh
pip install tiledistillery
tiledistillery plan --config tiles/config.json --process tiles/process.lua \
  --layer my-layer --attribution "My Layer, data (c) OpenStreetMap contributors, ODbL" \
  --regions europe/monaco,europe/andorra --shards 2
tiledistillery work --shard 0
tiledistillery work --shard 1
tiledistillery merge --layer my-layer
```

`plan` writes `plan/`. Each `work` builds one shard and may run on its own
machine, given `plan/` and the same files. `merge` needs every shard's
`parts/N/` and writes `layers/my-layer.pmtiles`. The
[documentation](https://github.com/tilelab/tiledistillery/blob/main/docs/README.md)
covers the rest.

## License and attribution

The code is
[MIT](https://github.com/tilelab/tiledistillery/blob/main/LICENSE)-licensed.
Layers built from OpenStreetMap data are © OpenStreetMap contributors under
the [Open Database License](https://www.openstreetmap.org/copyright), which
the `attribution` should name.
