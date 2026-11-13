r"""Running tools whose \r-redrawn progress, such as curl's, floods logs."""
import io
import re
import subprocess
import sys
import time
from typing import cast

_TERMINATOR: re.Pattern[bytes] = re.compile(rb"(\r|\n)")


def run_throttled(command: list[str], interval: float,
                  exclude: re.Pattern[bytes] | None = None) -> int:
    r"""Returns `command`'s exit code, its output copied to stderr.

    Log viewers such as GitHub Actions' print every \r redraw as a line of
    its own. \n lines pass through at once; of the redraws only the latest is
    kept, printed once `interval` seconds have passed, and dropped by the
    next \n line.

    Args:
        command: The tool and its arguments.
        interval: Minimum seconds between two printed redraws.
        exclude: Drops the \n lines it matches in full, such as a banner.
    """
    process: subprocess.Popen[bytes]
    with subprocess.Popen(command, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT) as process:
        source: io.BufferedReader = cast(io.BufferedReader, process.stdout)
        sink: io.BufferedWriter = cast(io.BufferedWriter, sys.stderr.buffer)
        last_printed: float = time.monotonic()
        pending: bytes | None = None  # The latest redraw not printed yet.
        rest: bytes = b""  # Text whose terminator has not arrived yet.
        chunk: bytes
        pieces: list[bytes]
        text: bytes
        terminator: bytes
        while chunk := source.read1(65536):
            *pieces, rest = _TERMINATOR.split(rest + chunk)
            for text, terminator in zip(pieces[::2], pieces[1::2]):
                if terminator == b"\n":
                    if not (exclude and exclude.fullmatch(text)):
                        sink.write(text + b"\n")
                    pending = None
                elif text.strip():  # A blank redraw only erases the last.
                    pending = text
            if (pending is not None
                    and time.monotonic() - last_printed >= interval):
                sink.write(pending + b"\n")
                last_printed = time.monotonic()
                pending = None
            sink.flush()
        leftover: bytes | None
        for leftover in (pending, rest):
            if leftover:
                sink.write(leftover + b"\n")
        sink.flush()
    return process.returncode
