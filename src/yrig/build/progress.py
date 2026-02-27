from __future__ import annotations


class ProgressStep:
    def __init__(self, name: str, weight: float = 1):
        self.name = name
        self._weight = weight
        self._progress: float = 0.0
        self._child_steps: list[ProgressStep] = []
        self._parent: ProgressStep | None = None
        self._child_weight_sum: float = 0
        self._finished: bool = False

    def get_progress(self):
        return self._progress

    def add_child_step(self, step: ProgressStep):
        step._parent = self
        self._child_steps.append(step)
        self._child_weight_sum += step._weight

    def get_child_steps(self) -> list[ProgressStep]:
        return self._child_steps

    def _update_progress_from_children(self):
        cumulative_progress = 0
        if all(child._finished for child in self._child_steps):
            self._set_finished()
            return

        for child in self._child_steps:
            child_progress = child.get_progress()
            scaled_progress = child_progress * (child._weight / self._child_weight_sum)
            cumulative_progress += scaled_progress
        self._progress = cumulative_progress
        self._propogate_progress()

    def _propogate_progress(self):
        if self._parent is not None:
            self._parent._update_progress_from_children()

    def update_progress(self, progress: float):
        if self._child_steps:
            return
        if progress == 1:
            self.finish_step()
            return
        self._progress = progress
        self._propogate_progress()

    def _set_finished(self):
        self._finished = True
        self._progress = 1

    def finish_step(self):
        for child in self._child_steps:
            child.finish_step()
        self._set_finished()
        self._propogate_progress()
