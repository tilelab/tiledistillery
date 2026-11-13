"""The layers a run builds, from `plan`'s comma-separated flags.

`--config`, `--process` and `--layer` pair up by position. tilemaker runs
in the working directory and sees nothing else, so the paths are relative
to it and stay inside it.
"""
import dataclasses
import os
import re

# A file name and an artifact name.
_NAME: re.Pattern[str] = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


@dataclasses.dataclass(frozen=True)
class Layer:
    """One output of every region.

    Attributes:
        name: The layer's name, which names its files.
        config: tilemaker's JSON config, relative to the working directory.
        process: tilemaker's Lua process script, likewise.
    """

    name: str
    config: str
    process: str


def _path(flag: str, value: str) -> str:
    """Returns a file's path, checked.

    Raises:
        ValueError: If it isn't a relative path to a file inside the
            working directory.
    """
    if (os.path.isabs(value)
            or os.path.normpath(value).split(os.sep)[0] == os.pardir):
        raise ValueError(f"{flag} {value!r} must be relative to the working "
                         f"directory and stay inside it, as tilemaker sees "
                         f"nothing else")
    if not os.path.isfile(value):
        raise ValueError(f"{flag} {value!r}: no such file")
    return value


def _split(value: str) -> list[str]:
    """Returns a comma-separated list's entries."""
    return [entry.strip() for entry in value.split(",")]


def parse_layers(configs: str, processes: str,
                 layer_names: str) -> list[Layer]:
    """Returns the layers the three comma-separated lists name.

    Raises:
        ValueError: If the lists differ in length, a name is invalid or
            repeated, or a path is invalid.
    """
    config_list: list[str] = _split(configs)
    process_list: list[str] = _split(processes)
    names: list[str] = _split(layer_names)
    if not len(config_list) == len(process_list) == len(names):
        raise ValueError(f"--config has {len(config_list)} entries, "
                         f"--process {len(process_list)}, --layer "
                         f"{len(names)}; they must pair up 1:1")
    name: str
    for name in names:
        if not _NAME.fullmatch(name):
            raise ValueError(f"--layer {name!r} must be letters, digits, "
                             f"'.', '_' and '-', starting with a letter or "
                             f"digit")
    if len(set(names)) < len(names):
        raise ValueError(f"--layer {layer_names!r} repeats a name")
    config: str
    process: str
    return [Layer(name, _path("--config", config), _path("--process", process))
            for config, process, name in zip(config_list, process_list, names)]
