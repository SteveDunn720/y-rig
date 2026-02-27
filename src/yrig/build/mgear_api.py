from __future__ import annotations

import json
import logging
from collections.abc import Callable
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import dataclass
from io import TextIOBase
from pathlib import Path
from typing import Iterator, Sequence

from yrig.build.context import temp_asset_root
from yrig.build.progress import ProgressStep

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
def _redirect_external_logger(external_logger: logging.Logger, target_logger: logging.Logger):
    """Temporarily hooks an external logger into a specified target."""

    # Store original state
    original_parent = external_logger.parent
    original_propagate = external_logger.propagate

    try:
        external_logger.parent = target_logger
        external_logger.propagate = True
        yield external_logger
    finally:
        # Restore original state exactly as it was
        external_logger.parent = original_parent
        external_logger.propagate = original_propagate


@contextmanager
def _capture_mgear_logs():
    import mgear.pymaya

    def display_info(msg: str):
        log.info(msg)

    def display_warning(msg: str):
        log.warning(msg)

    def display_error(msg: str):
        log.error(msg)

    original_info = mgear.pymaya.displayInfo
    original_warning = mgear.pymaya.displayWarning
    original_error = mgear.pymaya.displayError

    try:
        mgear.pymaya.displayInfo = display_info  # type: ignore
        mgear.pymaya.displayWarning = original_warning  # type: ignore
        mgear.pymaya.displayError = display_error  # type: ignore
        yield

    finally:
        mgear.pymaya.displayInfo = original_info  # type: ignore
        mgear.pymaya.displayWarning = original_warning  # type: ignore
        mgear.pymaya.displayError = original_error  # type: ignore


@contextmanager
def _capture_mgear_output():
    """Redirect sys.stdout and sys.stderr into this module's logger."""

    stdout_logger = StdoutToLogger(log)
    stderr_logger = StdoutToLogger(log, logging.ERROR)

    with (
        redirect_stdout(stdout_logger),
        redirect_stderr(stderr_logger),
    ):
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
        self._build_prefix_set: set[str] = set(f"{step.name} : " for step in build_steps)
        self._custom_step_prefix_set: set[str] = {
            "SUCCEED: Custom Shifter Step Class: ",
        }
        self._valid_prefix_set = self._build_prefix_set | self._custom_step_prefix_set

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()

        return any(message.startswith(prefix) for prefix in self._valid_prefix_set)


class ProgressLogHandler(logging.Handler):
    def __init__(
        self,
        pre_steps: Sequence[BuildStep],
        build_steps: Sequence[BuildStep],
        post_steps: Sequence[BuildStep],
        number_of_components: int,
        progress_callback: Callable[[float, str | None], None] | None = None,
    ):
        super().__init__()
        self.progress_callback = progress_callback
        self.pre_steps = pre_steps
        self.build_steps = build_steps
        self.post_steps = post_steps
        self.addFilter(BuildStepFilter(build_steps))
        self.number_of_components = number_of_components

        self.pre_step_names: list[str] = [step.name for step in self.pre_steps]
        self.post_step_names: list[str] = [step.name for step in self.post_steps]

        self.root_step = ProgressStep("Rig Build")
        self.pre_build = ProgressStep("Pre Build", len(pre_steps) * 0.1)
        self.pre_step_map: dict[str, ProgressStep] = {}
        self.root_step.add_child_step(self.pre_build)
        for step in self.pre_steps:
            step_progress = ProgressStep(step.name, weight=step.weight)
            self.pre_build.add_child_step(step_progress)
            self.pre_step_map[step.name] = step_progress
        self.pre_step_finished: bool = False

        # Main Build Steps
        self.build_step = ProgressStep("Main Build", 10)
        self.build_step_map: dict[str, ProgressStep] = {}
        self.root_step.add_child_step(self.build_step)
        for step in self.build_steps:
            step_progress = ProgressStep(step.name, weight=step.weight)
            self.build_step.add_child_step(step_progress)
            self.build_step_map[step.name] = step_progress
            # Add leaf steps for components
            for i in range(number_of_components):
                step_progress.add_child_step(ProgressStep(f"{step.name}_component{i}", weight=1))
        self.build_step_finished: bool = False

        self.post_build = ProgressStep("Post Build", len(post_steps))
        self.post_step_map: dict[str, ProgressStep] = {}
        self.root_step.add_child_step(self.post_build)
        for step in self.post_steps:
            step_progress = ProgressStep(step.name, weight=step.weight)
            self.post_build.add_child_step(step_progress)
            self.post_step_map[step.name] = step_progress
        self.post_step_finished: bool = False

        self.build_step_counter: dict[str, int] = {}

    def _report_progress(self, progress: float, step_name: str | None = None):
        if self.progress_callback:
            try:
                self.progress_callback(progress, step_name)
            except Exception:
                pass

    def _on_build_step_progress(self, step_name: str):
        if not self.pre_step_finished:
            self.pre_build.finish_step()
            self.pre_step_finished = True
        if step_name in self.build_step_counter:
            self.build_step_counter[step_name] += 1
        else:
            self.build_step_counter[step_name] = 1
        step = self.build_step_map.get(step_name)
        if step is not None:
            step.get_child_steps()[self.build_step_counter[step_name] - 1].finish_step()
        self._report_progress(self.root_step.get_progress(), step_name)

    def _on_custom_step_finished(self, step_name: str):
        if step_name in self.pre_step_names:
            self.pre_step_map[step_name].finish_step()
        if step_name in self.post_step_names:
            if not self.post_step_finished:
                self.build_step.finish_step()
                self.post_step_finished = True
            self.post_step_map[step_name].finish_step()
        self._report_progress(self.root_step.get_progress(), step_name)

    def emit(self, record: logging.LogRecord):
        message = record.getMessage()

        if message.startswith("SUCCEED: Custom Shifter Step Class: "):
            path = message.split(": ")[2].rsplit(".", 1)[0]
            step_name = path
            self._on_custom_step_finished(step_name)
            return

        prefix = message.partition(" : ")[0]
        step_name = prefix
        self._on_build_step_progress(step_name)


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

    # Get the guide data from the file
    guide_data: dict = io._import_guide_template(file_path)
    param_values = guide_data["guide_root"]["param_values"]

    # Set WIP mode in the mgear guide data if we're doing a dev build
    param_values["mode"] = 1 if dev_build else 0

    # Get the relevant steps of the build (progress reporting)
    pre_custom_step: dict = json.loads(param_values["preCustomStep"])
    post_custom_step: dict = json.loads(param_values["postCustomStep"])
    pre_custom_steps: list[BuildStep] = [
        BuildStep(item["path"]) for item in pre_custom_step["items"]
    ]
    post_custom_steps: list[BuildStep] = [
        BuildStep(item["path"]) for item in post_custom_step["items"]
    ]
    num_components = len(guide_data["components_list"])

    rig = Rig()
    progress_handler = ProgressLogHandler(
        pre_custom_steps, BUILD_STEPS, post_custom_steps, num_components, progress_callback
    )
    with (
        _capture_mgear_output(),
        _capture_mgear_logs(),
        _temporary_log_handler(log, progress_handler),
    ):
        log.info("\n" + "= SHIFTER RIG SYSTEM " + "=" * 46)

        rig.stopBuild = False

        rig.guide.set_from_dict(guide_data)

        # Build
        log.info("\n" + "= BUILDING RIG " + "=" * 46)
        # Get merged options early so custom steps use blueprint values
        merged_options = rig.guide.getMergedOptions()
        rig.from_dict_custom_step(merged_options, pre=True)
        rig.build()

        # Check if build was cancelled
        if rig.stopBuild:
            log.info("\n" + "= SHIFTER BUILD CANCELLED " + "=" * 40)
            return None

        rig.from_dict_custom_step(merged_options, pre=False)

        # controls shapes buffer
        if guide_data["ctl_buffers_dict"]:
            curve.update_curve_from_data(
                guide_data["ctl_buffers_dict"], rplStr=["_controlBuffer", ""]
            )
    return rig


def build_from_path(
    rig_root_path: Path,
    dev_build: bool = False,
    progress_callback: Callable[[float, str | None], None] | None = None,
):
    """Build an mGear Shifter rig from a rig path.

    Args:
        rig_root_path: Path to an a rig file structure.
        dev_build: When true the mGear shifter build will be set to WIP mode.
        progress_callback: A function to call at each step of the build.
            It will be called with a float (overall progress from 0-1) and a string (the current step)
    """

    guide_path = rig_root_path / "data/guide.sgt"
    with temp_asset_root(rig_root_path):
        log.info("Starting mGear Shifter build from file: %s", guide_path)
        try:
            _build_from_shifter_file(guide_path, dev_build, progress_callback)
        except Exception as e:
            log.error("mGear build failed: %s", e)
            raise RuntimeError(f"mGear Shifter build failed for '{guide_path.name}': {e}") from e
        log.info("Build from file complete.")
