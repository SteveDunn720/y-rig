from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import mgear.shifter.custom_step as cstp

from yrig.build import BuildScope
from yrig.build.context import get_build_scope
from yrig.build.nxt_api import execute_nxt_graph

if TYPE_CHECKING:
    from mgear.shifter import Rig

    from ..pre.paths import CustomShifterStep as PathsStep

log = logging.getLogger(__name__)


class CustomShifterStep(cstp.customShifterMainStep):
    """
    This step calls a face build step defined as an NXT graph.
    """

    def setup(self) -> None:
        """
        Setting the name property makes the custom step accessible
        in later steps.

        i.e: Running  self.custom_step("{name}")  from steps ran after
             this one, will grant this step.
        """
        self.name = "build_face"

    def run(self) -> None:
        """Run method.

            i.e:  self.mgear_run.global_ctl
                gets the global_ctl from shifter rig build base

            i.e:  self.component("control_C0").ctl
                gets the ctl from shifter component called control_C0

            i.e:  self.custom_step("otherCustomStepName").ctlMesh
                gets the ctlMesh from a previous custom step called
                "otherCustomStepName"

        Returns:
            None: None
        """
        # Skip this step if we're building only the body
        build_scope = get_build_scope()
        if build_scope is BuildScope.BODY:
            return

        paths_step: PathsStep = self.custom_step("paths")
        data_path: Path = paths_step.rig_data_path
        face_path: Path = data_path / "face"
        face_graph_path: Path = face_path / "build.nxt"
        if not face_path.exists():
            raise RuntimeError(f"No face description graph found at {face_graph_path}")
        log.info(f"Building face from graph at: {face_graph_path}")
        execute_nxt_graph(face_graph_path)
