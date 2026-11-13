# Build your first layer

You build a layer of waste baskets for Monaco and Andorra on your own
machine, look at it, and then build it for the whole world on GitHub
Actions. You need what the README's
[Anywhere else](../../README.md#anywhere-else) lists: macOS or Linux, or
Windows with WSL, Python 3.11 or later, Docker and tippecanoe's
`tile-join`.

## Step 1: Install tiledistillery

```sh
mkdir bins && cd bins
python3 -m venv .venv && source .venv/bin/activate
pip install tiledistillery
```

## Step 2: Write the tilemaker config

[tilemaker](https://github.com/systemed/tilemaker) builds the tiles. Its
JSON config names the vector layers inside the file and their zoom levels.
Save this as `tiles/config.json`:

```json
{
  "layers": {
    "bins": { "minzoom": 10, "maxzoom": 14 }
  },
  "settings": {
    "minzoom": 10,
    "maxzoom": 14,
    "basezoom": 14,
    "include_ids": false,
    "name": "Waste baskets",
    "version": "1.0",
    "description": "Public waste baskets from OpenStreetMap",
    "compress": "gzip"
  }
}
```

## Step 3: Write the process script

tilemaker calls the Lua script's `node_function` for each OpenStreetMap
node, and it decides what goes into which vector layer. Save this as
`tiles/process.lua`:

```lua
node_keys = { "amenity" }

function node_function()
  if Find("amenity") == "waste_basket" then
    Layer("bins", false)
  end
end

function way_function()
end
```

`node_keys` hands it only nodes with an `amenity` tag, and
`Layer("bins", false)` adds the node to `bins` as a point. Ways are
skipped.

## Step 4: Build the layer

```sh
tiledistillery plan --config tiles/config.json --process tiles/process.lua \
  --layer bins --attribution "Waste baskets, data (c) OpenStreetMap contributors, ODbL" \
  --regions europe/monaco,europe/andorra --shards 2
tiledistillery work --shard 0
tiledistillery work --shard 1
tiledistillery merge --layer bins
```

- `plan` lists Geofabrik's extracts and keeps the two `--regions` names.
  Each extract is a **region**. It splits them into two **shards**, the
  parts that each `work` builds, and writes `plan/`.
- Each `work` downloads its shard's region and runs tilemaker on it in
  Docker, which pulls tilemaker's image the first time. The two could run
  on two machines, each with `plan/` and `tiles/`.
- `merge` joins both shards' tiles into one file. It ends with
  `merged 2 region(s) into layers/bins.pmtiles`.

`--attribution` goes into the layer's metadata, as OpenStreetMap's license
requires. To build again, delete the run first with `rm -r plan extracts
parts`, as `plan` won't start over another run.

## Step 5: Look at it

Drop `layers/bins.pmtiles` onto [pmtiles.io](https://pmtiles.io) and zoom
in to Monaco: each point is a waste basket.

## Step 6: Build it for the world

Commit `tiles/` and this workflow to a GitHub repository, but not `.venv/`
or the run's directories:

```yaml
# .github/workflows/bins.yml
on: workflow_dispatch

jobs:
  build:
    uses: tilelab/tiledistillery/.github/workflows/_pipeline.yml@v1.0.0
    permissions:
      contents: read
    with:
      config: tiles/config.json
      process: tiles/process.lua
      layer: bins
      attribution: "Waste baskets, data (c) OpenStreetMap contributors, ODbL"
```

Start it from the repository's Actions tab. Without `regions`, it builds
every region Geofabrik has, in 20 shards: the jobs are `plan`, `work` once
per shard and `merge`. The run's summary then lists the artifact
`bins-pmtiles` with `bins.pmtiles`. For a shorter first run, add
`regions: europe/monaco,europe/andorra`.

## Next steps

- To publish the layer as a GitHub Release, see
  [`_publish-release.yml`](../reference/workflows.md#_publish-releaseyml).
- To build several layers from one download, give `plan` lists; see the
  [command line](../reference/cli.md#tiledistillery-plan).
- tilemaker's
  [configuration guide](https://github.com/systemed/tilemaker/blob/master/docs/CONFIGURATION.md)
  covers configs and process scripts in full.
