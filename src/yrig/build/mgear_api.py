import logging
from collections.abc import Callable
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import TextIOBase
from pathlib import Path
from typing import Iterator

log = logging.getLogger(__name__)


class StdoutToLogger(TextIOBase):
    """A write-only stream that forwards each line to a Python logger.

    mGear calls ``sys.stdout.write()`` directly rather than using the
    ``logging`` module, so we temporarily replace ``sys.stdout`` with one
    of these to capture its output.
    """

    def __init__(self, logger: logging.Logger, level: int = logging.INFO) -> None:
        self._logger = logger
        self._level = level
        self._buffer = ""

    def write(self, message: str) -> int:
        self._buffer += message
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self._logger.log(self._level, line)
        return len(message)

    def flush(self) -> None:
        if self._buffer.strip():
            self._logger.log(self._level, self._buffer.strip())
            self._buffer = ""


@contextmanager
def _capture_mgear_output() -> Iterator[None]:
    """Redirect sys.stdout and sys.stderr into the logger."""

    stdout_logger = StdoutToLogger(log)
    stderr_logger = StdoutToLogger(log, logging.ERROR)

    with redirect_stdout(stdout_logger), redirect_stderr(stderr_logger):
        yield


def _build_from_shifter_file(file_path: Path, dev_build: bool):
    from mgear.core import curve
    from mgear.shifter import Rig, io

    guide_data: dict = io._import_guide_template(file_path)
    guide_data["guide_root"]["param_values"]["mode"] = 1 if dev_build else 0
    rig = Rig()
    with _capture_mgear_output():
        rig.buildFromDict(guide_data)
        # controls shapes buffer
        if guide_data["ctl_buffers_dict"]:
            curve.update_curve_from_data(
                guide_data["ctl_buffers_dict"], rplStr=["_controlBuffer", ""]
            )
    return rig


def build_from_file(
    file_path: Path,
    dev_build: bool = False,
    progress_callback: Callable[[float, str | None], None] | None = None,
) -> None:
    """Build an mGear Shifter rig from a guide template file.

    Args:
        file_path: Path to an ``.sgt`` guide template file.
        dev_build: When true the mGear shifter build will be set to WIP mode.
        progress_callback: A function to call at each step of the build.
            It will be called with a float (overall progress from 0-1) and a string (the current step)
    """

    log.info("Starting mGear Shifter build from file: %s", file_path)
    try:
        _build_from_shifter_file(file_path, dev_build)

    except Exception as e:
        log.error("mGear build failed: %s", e)
        raise RuntimeError(f"mGear Shifter build failed for '{file_path.name}': {e}") from e
    log.info("Build from file complete.")
