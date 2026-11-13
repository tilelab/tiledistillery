# How the pipeline works

Why tiledistillery is built the way it is. Details of one mechanism are in
code comments next to it.

## Regions

A region is one extract a source lists. Geofabrik's are its leaves:
extracts with no finer one below them, such as `europe/germany/bavaria`
(`sources/geofabrik.py`). Regions are never split or joined, so Russia and
Vatican City are one region each. A handful of leaves that finer extracts
already cover, such as `dach`, are skipped by a hand-kept list, because
Geofabrik's index doesn't mark them.

## Shards planned up front

`plan` gives every worker its regions before any starts, so the workers
share nothing while they run and need no service to coordinate through.
That is what lets the steps run anywhere: an Actions matrix, a job array,
or a shell loop.

A queue that idle workers claim from would balance better, since it adapts
to slow downloads and slow runners as they happen. It needs shared state
with atomic writes, though, which ties the pipeline to one place to keep
it. The plan costs some wall-clock time at the end of a run, but no runner
time: a worker that finishes early just stops.

The split gives each shard about equal `.osm.pbf` bytes. Recorded build
times predicted no better than size, as most of a region's time is its
download, whose speed varies from run to run. So no state is kept between
runs either.

## Several layers, one download

With several layers, a worker downloads each region once and runs tilemaker
once per layer on it. The region is the unit of work: if one layer fails,
the region fails and leaves no tiles for any layer. `merge` then joins one
layer's tiles from every shard with one `tile-join`, which, unlike
`pmtiles merge`, accepts the border and low-zoom tiles that neighboring
regions share.

## Failures

A failed download or build is not retried, since curl already retries
transient errors. The shard goes on without the region and warns about it,
and so does every merge that lacks it. A worker that dies leaves its shard
incomplete, and `merge` refuses to run until it is built again.

## Why tilemaker

Planetiler's strength is building the whole planet on one machine, which a
pipeline of regional extracts doesn't need. tilemaker builds an extract
from two plain files, a JSON config and a Lua script, while Planetiler's
stable interface is a compiled Java profile. Every build uses tilemaker's
`--store` on disk, so memory doesn't depend on a region's size.

tilemaker runs in Docker, with `ghcr.io/systemed/tilemaker:master`, the only
tag upstream publishes; Ubuntu's package is too old.

## On GitHub Actions

Every job checks out tiledistillery at `job.workflow_sha`, the commit the
caller's `uses:` resolved to, and runs `.github/actions/setup` from there,
because a remote `uses:` reference can't be an expression. Where that is
empty, as on GitHub Enterprise Server, the run fails rather than build
another commit. The calling repository is checked out at the job's root,
where every step runs. So the inputs' paths are relative to it, and
tilemaker, which in Docker sees only the working directory, finds the
configs and every file they name.
