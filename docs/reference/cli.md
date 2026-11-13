# Command-line reference

`tiledistillery` runs the pipeline's three steps in a shared working
directory: `plan` once, `work` once per shard, `merge` once per layer.
`--version` prints the version, and `-h` prints help for any step. Exit
status: `0` on success, `1` when a step fails, `2` for invalid arguments.
An empty option value counts as not given. On Windows outside WSL, every
step fails at once.

## tiledistillery plan

```sh
tiledistillery plan --config PATHS --process PATHS --layer NAMES \
  --attribution TEXT [--source NAME] [--regions IDS] [--shards N]
```

Run once. It asks the source for its regions, keeps those in scope, asks
each extract's size with a `HEAD` request, and splits them into shards of
about equal bytes. It writes `plan/plan.json`.

| Option | Default | Description |
| --- | --- | --- |
| `--config PATHS` | Required | tilemaker's JSON config, or a comma-separated list, one per layer. |
| `--process PATHS` | Required | tilemaker's Lua process script, or a list like `--config`. |
| `--layer NAMES` | Required | The layer's name, or a list like `--config`, such as `bins,roads`: letters, digits, `.`, `_` and `-`, starting with a letter or digit. It names the layer's file. |
| `--attribution TEXT` | Required | Written into every layer's metadata. |
| `--source NAME` | `geofabrik` | The [source](sources.md) of the regions. |
| `--regions IDS` | All | Comma-separated region ids, each with every region below it: `europe` selects every region in Europe, such as `europe/france/alsace`, and `europe/monaco,europe/andorra` only those two. |
| `--shards N` | `1` | How many shards to split the run into; fewer if there are fewer regions. |

The three lists pair up by position. tilemaker runs in the working
directory and sees nothing outside it, so paths are relative to it, and so
are the files the configs and scripts name.

It fails if the working directory holds `plan/`, `extracts/` or `parts/`,
the lists don't pair up, a file is missing or outside the working
directory, a name is invalid or repeats, the source isn't installed, or a
`--regions` id matches no region.

## tiledistillery work

```sh
tiledistillery work --shard N [--tilemaker-image IMAGE]
```

Run once per shard, beside `plan/` and the files `plan` was given, at the
same paths. For each of the shard's regions, largest first, it downloads
the extract with `curl` and runs tilemaker in Docker once per layer. It
replaces `parts/N/`.

| Option | Default | Description |
| --- | --- | --- |
| `--shard N` | Required | Which of the plan's shards to build, counted from 0. |
| `--tilemaker-image IMAGE` | `ghcr.io/systemed/tilemaker:master` | The tilemaker Docker image. |

A region whose download or build fails is not retried: no layer gets any
of it, and the step warns and goes on.

## tiledistillery merge

```sh
tiledistillery merge --layer NAME
```

Run once per layer, after every shard, with one of the names `plan` got
as `--layer`. It joins `parts/*/<layer>/` with `tile-join` from
[tippecanoe](https://github.com/felt/tippecanoe) into
`layers/<layer>.pmtiles`, replacing it. It fails if a shard hasn't recorded
every one of its regions, no region was built, or `tile-join` isn't on
`PATH`, and it warns with the failed regions the layer lacks.

## Run directory

```
plan/plan.json        written by plan
extracts/             shard N's current region, while it builds
  N.osm.pbf
  N.store/            tilemaker's --store
parts/N/              written by work --shard N
  outcomes.jsonl      a JSON line per region: region_id, error or null
  <layer>/<region>.pmtiles
layers/<layer>.pmtiles  written by merge
```

A region's file name is its id with `/` as `_`. Every step after `plan`
refuses a `plan/` that another tiledistillery version wrote, so a run uses
one version throughout.

## Log output

Every step logs to stderr. Each region's log is a group, and warnings are
one line each. Three environment variables format them, with `{title}` and
`{message}` as placeholders:

| Variable | Default |
| --- | --- |
| `TILEDISTILLERY_LOG_WARNING` | `warning: {title}: {message}` |
| `TILEDISTILLERY_LOG_GROUP` | `{title}:` |
| `TILEDISTILLERY_LOG_END_GROUP` | Empty, no line |

`_pipeline.yml` sets them to GitHub's workflow commands, which makes
warnings annotations and folds each region.
