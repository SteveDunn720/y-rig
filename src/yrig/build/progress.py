from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable, Generator

_current_progress: ContextVar[ProgressStep | None] = ContextVar("_current_progress", default=None)


@contextmanager
def progress_step(
    name: str, weight: float = 1.0, total: float | None = None
) -> Generator[ProgressStep, None, None]:
    parent = _current_progress.get()

    step = ProgressStep(name, weight, total)
    if parent:
        parent.add_child_step(step)
    token = _current_progress.set(step)
    try:
        yield step
    finally:
        step.finish_step()
        _current_progress.reset(token)


@contextmanager
def bind_progress_step(step: ProgressStep) -> Generator[ProgressStep, None, None]:
    parent = _current_progress.get()
    if parent:
        parent.add_child_step(step)
    token = _current_progress.set(step)
    try:
        yield step
    finally:
        step.finish_step()
        _current_progress.reset(token)


def get_current_progress_step() -> ProgressStep | None:
    return _current_progress.get()


def progress_update(value: float) -> None:
    step = _current_progress.get()
    if step:
        step.update_progress(value)


def finish_step() -> None:
    step = _current_progress.get()
    if step:
        step.finish_step()


class ProgressStep:
    def __init__(
        self,
        name: str,
        weight: float = 1,
        total_weight: float | None = None,
        callback: Callable[[float, str], None] | None = None,
    ) -> None:
        self.name = name
        self._weight = weight
        self._progress: float = 0.0
        self._children: list[ProgressStep] = []
        self._parent: ProgressStep | None = None
        self._total_weight: float | None = total_weight
        self._child_weight_sum: float = 0
        self._finished: bool = False
        self._callback = callback

    def get_progress(self) -> float:
        return self._progress

    def add_child_step(self, step: ProgressStep) -> None:
        step._parent = self
        self._children.append(step)
        self._child_weight_sum += step._weight

    def get_child_steps(self) -> list[ProgressStep]:
        return self._children

    def _update_progress_from_children(self) -> None:
        if not self._children:
            return
        denominator = self._total_weight or self._child_weight_sum
        cumulative_progress = 0
        for child in self._children:
            child_progress = child.get_progress()
            scaled_progress = child_progress * (child._weight / denominator)
            cumulative_progress += scaled_progress
        self._progress = cumulative_progress
        self._propogate_progress()

    def _propogate_progress(self) -> None:
        if self._parent is not None:
            self._parent._update_progress_from_children()
        elif self._callback is not None:
            current_step = get_current_progress_step() or self
            name_path = "/".join(s.name for s in current_step.get_ancestors())
            try:
                self._callback(self._progress, name_path)
            except Exception:
                pass

    def update_progress(self, progress: float) -> None:
        if self._children:
            return
        if progress == 1:
            self.finish_step()
            return
        self._progress = max(0.0, min(1.0, progress))
        self._propogate_progress()

    def _set_finished(self) -> None:
        self._finished = True
        self._progress = 1

    def finish_step(self) -> None:
        if self._finished:
            return
        for child in self._children:
            child.finish_step()
        self._set_finished()
        self._propogate_progress()

    def get_ancestors(self) -> list[ProgressStep]:
        node: ProgressStep | None = self
        out: list[ProgressStep] = []
        while node is not None:
            out.append(node)
            node = node._parent
        return list(reversed(out))
