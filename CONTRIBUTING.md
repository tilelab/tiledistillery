# Contributing to tiledistillery

Code and documentation follow tilealchemist's
[CONTRIBUTING.md](https://github.com/tilelab/tilealchemist/blob/main/CONTRIBUTING.md).
GitHub-specific code stays in `.github/`.

## Set up

```sh
git clone https://github.com/tilelab/tiledistillery.git && cd tiledistillery
python3 -m venv .venv && source .venv/bin/activate
pip install -e . --config-settings editable_mode=compat
pip install pylint==4.1.2 mypy==2.4.1 types-requests
```

## Run the checks

```sh
pylint tiledistillery
mypy
```

CI's `lint.yml` runs both, `ci.yml` the real `_pipeline.yml` on three
microstates. To try a change locally, run the steps from the
[README](README.md#anywhere-else) with the configs `ci.yml` passes.

## Release

Set `version` in `pyproject.toml` and push the tag `v<version>`.
`release.yml` checks that they match, runs `lint.yml` and `ci.yml`, and
publishes to PyPI. Raise the major version when a command, option, run
directory name, the source interface, or a workflow input or output
changes.

Each version can be published only once, so try a release as a candidate
such as `1.0.0rc1` first and retry a failed one as `rc2`. pip takes a
candidate only when it is named, or while no final release exists:

```sh
pip install tiledistillery==1.0.0rc1
```
