from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from io import TextIOBase
from pathlib import Path
from typing import Iterator, Sequence

log = logging.getLogger(__name__)


class StdoutToLogger(TextIOBase):
    """A write-only stream that forwards each line to a Python logger.

    mGear calls ``sys.stdout.write()`` directly rather than using the
    ``logging`` module, so we temporarily replace ``sys.stdout`` with one
    of these to capture its output.
    """

    def __init__(self, logger: logging.Logger, level: int = logging.INFO) -> None:
        self.logger = logger
        self.level = level
        self._buffer = ""

    def write(self, message: str) -> int:
        self._buffer += message
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self.logger.log(self.level, line)
        return len(message)

    def flush(self) -> None:
        if self._buffer.strip():
            self.logger.log(self.level, self._buffer.strip())
            self._buffer = ""


@contextmanager
def _capture_mgear_output() -> Iterator[None]:
    """Redirect sys.stdout and sys.stderr into the logger."""

    stdout_logger = StdoutToLogger(log)
    stderr_logger = StdoutToLogger(log, logging.ERROR)

    with redirect_stdout(stdout_logger), redirect_stderr(stderr_logger):
        yield


@contextmanager
def _temporary_log_handler(logger: logging.Logger, handler: logging.Handler) -> Iterator[None]:
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)


@dataclass
class BuildStep:
    name: str
    weight: float = 1


class BuildStepFilter(logging.Filter):
    def __init__(self, build_steps: Sequence[BuildStep]):
        super().__init__()
        self._prefix_set = set(f"{step.name} : " for step in build_steps)

    def filter(self, record: logging.LogRecord):
        message = record.getMessage()
        return any(prefix in message for prefix in self._prefix_set)


class ProgressLogHandler(logging.Handler):
    def __init__(
        self,
        build_steps: Sequence[BuildStep],
        number_of_components: int,
        progress_callback: Callable[[float, str | None], None] | None = None,
    ):
        super().__init__()
        self.progress_callback = progress_callback
        self.build_steps = build_steps
        self.addFilter(BuildStepFilter(build_steps))
        self.number_of_components = number_of_components
        self.build_step_counter: dict[str, int] = {}

        self.step_spans: dict[str, float] = {}
        self.step_offset: dict[str, float] = {}
        total_weight = sum(step.weight for step in self.build_steps)
        running_weight = 0
        for step in self.build_steps:
            normalized_weight = step.weight / total_weight
            self.step_offset[step.name] = running_weight
            self.step_spans[step.name] = normalized_weight
            running_weight += normalized_weight

    def emit(self, record: logging.LogRecord):
        message = record.getMessage()
        prefix = message.partition(" : ")[0]
        step_name = prefix
        if step_name in self.build_step_counter:
            self.build_step_counter[step_name] += 1
        else:
            self.build_step_counter[step_name] = 1
        start_offset = self.step_offset[step_name]
        step_span = self.step_spans[step_name]

        current_step_progress = min(
            (self.build_step_counter[step_name] / self.number_of_components), 1
        )
        progress = start_offset + (current_step_progress * step_span)
        if self.progress_callback:
            try:
                self.progress_callback(progress, step_name)
            except Exception:
                pass
        return


BUILD_STEPS: list[BuildStep] = [
    BuildStep("Init", 1),
    BuildStep("Objects", 5),
    BuildStep("Properties", 1),
    BuildStep("Operators", 1),
    BuildStep("Connect", 1),
    BuildStep("Joints", 1),
    BuildStep("Finalize", 1),
]


def _build_from_shifter_file(
    file_path: Path,
    dev_build: bool,
    progress_callback: Callable[[float, str | None], None] | None = None,
):
    from mgear.core import curve
    from mgear.shifter import Rig, io

    guide_data: dict = io._import_guide_template(file_path)
    num_components = len(guide_data["components_list"])

    guide_data["guide_root"]["param_values"]["mode"] = 1 if dev_build else 0

    rig = Rig()
    progress_handler = ProgressLogHandler(BUILD_STEPS, num_components, progress_callback)
    with _capture_mgear_output(), _temporary_log_handler(log, progress_handler):
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
        _build_from_shifter_file(file_path, dev_build, progress_callback)

    except Exception as e:
        log.error("mGear build failed: %s", e)
        raise RuntimeError(f"mGear Shifter build failed for '{file_path.name}': {e}") from e
    log.info("Build from file complete.")
