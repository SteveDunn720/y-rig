import logging
import sys
from contextlib import contextmanager
from io import TextIOBase
from pathlib import Path
from typing import Iterator

log = logging.getLogger(__name__)


class _StdoutToLogger(TextIOBase):
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
            self._logger.log(self._level, line)
        return len(message)

    def flush(self) -> None:
        if self._buffer.strip():
            self._logger.log(self._level, self._buffer.strip())
            self._buffer = ""


@contextmanager
def _capture_mgear_output() -> Iterator[None]:
    """Redirect sys.stdout and sys.stderr into the logger."""
    original_out = sys.stdout
    original_err = sys.stderr
    sys.stdout = _StdoutToLogger(log)
    sys.stderr = _StdoutToLogger(log, logging.ERROR)
    try:
        yield
    finally:
        captured_out = sys.stdout
        captured_err = sys.stderr
        sys.stdout = original_out
        sys.stderr = original_err
        captured_out.flush()
        captured_err.flush()


def _build_from_shifter_file(file_path: Path, dev_build: bool):
    from mgear.core import curve
    from mgear.shifter import Rig, io

    guide_data: dict = io._import_guide_template(file_path)
    guide_data["guide_root"]["param_values"]["mode"] = 1 if dev_build else 0
    rig = Rig()
    rig.buildFromDict(guide_data)
    # controls shapes buffer
    if guide_data["ctl_buffers_dict"]:
        curve.update_curve_from_data(guide_data["ctl_buffers_dict"], rplStr=["_controlBuffer", ""])
    return rig


def build_from_file(file_path: Path, dev_build: bool = False) -> None:
    """Build an mGear Shifter rig from a guide template file.

    Args:
        file_path: Path to an ``.sgt`` guide template file.
    """

    log.info("Starting mGear Shifter build from file: %s", file_path)
    try:
        with _capture_mgear_output():
            _build_from_shifter_file(file_path, dev_build)

    except Exception as e:
        log.error("mGear build failed: %s", e)
        raise RuntimeError(f"mGear Shifter build failed for '{file_path.name}': {e}") from e
    log.info("Build from file complete.")
