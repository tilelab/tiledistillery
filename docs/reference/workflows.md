# Workflows reference

Two reusable GitHub Actions workflows. Callers pin a release, such as
`@v1.0.0`.

## _pipeline.yml

```yaml
uses: tilelab/tiledistillery/.github/workflows/_pipeline.yml@v1.0.0
permissions:
  contents: read
```

Builds one or more layers from Geofabrik, with `plan`'s
[options](cli.md#tiledistillery-plan). All inputs are strings; empty means
unset.

| Input | Default | Description |
| --- | --- | --- |
| `config` | Required | The tilemaker JSON config's path in the calling repository, or a comma-separated list, one per layer. |
| `process` | Required | The tilemaker Lua process script's path, or a list like `config`. |
| `layer` | Required | The layer's name, or a list like `config`, such as `bins,roads`. |
| `attribution` | Required | Written into every layer's metadata. |
| `shards` | `20` | Number of shards, one worker job each. 20 fills GitHub Free's concurrent jobs. |
| `regions` | Empty, the world | Comma-separated region ids, each with every region below it, such as `europe` or `europe/monaco,europe/andorra`. |

`plan` and `work` check out the calling commit at the root, so paths are
relative to the repository; that needs the `contents: read` permission.
The pipeline writes nothing to the calling repository and keeps nothing
between runs.

Each layer comes back as the artifact `<layer>-pmtiles` holding
`<layer>.pmtiles`.

The jobs are `plan`, `work` (one per shard) and `merge` (one per layer).
Matrix jobs don't cancel each other, so after a failed shard, "Re-run failed
jobs" builds only that shard again. Every job runs the same tiledistillery
commit, and warnings show up as annotations.

## _publish-release.yml

```yaml
publish:
  needs: build
  uses: tilelab/tiledistillery/.github/workflows/_publish-release.yml@v1.0.0
  permissions:
    contents: write
  with:
    layer: bins
    tag: bins-latest
    title: "Waste baskets"
```

Publishes one `<layer>-pmtiles` artifact as a GitHub Release of the calling
repository, with its own token. It uploads into the draft `<tag>-draft`,
retrying each asset and checking its size, and only then replaces the old
release under `tag`, and the tag. A failed upload leaves the old release
in place, and the next run replaces the draft.

| Input | Default | Description |
| --- | --- | --- |
| `layer` | Required | The layer's name. |
| `tag` | Required | The release tag, such as `bins-latest`. |
| `title` | Required | The release title. |

A layer over 2000 MiB is split into `<layer>.pmtiles.partNNN` assets, as
GitHub limits an asset to 2 GiB. The release notes give a
`gh release download` command that also joins the parts.
