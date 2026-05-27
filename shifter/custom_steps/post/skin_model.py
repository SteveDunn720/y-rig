from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import mgear.shifter.custom_step as cstp
from maya import cmds

from yrig.skin import skin_and_apply_weights_from_directory
from yrig.skin.core import remove_unused_influences, skin_geometry

if TYPE_CHECKING:
    from mgear.shifter import Rig

    from ..pre.paths import CustomShifterStep as PathsStep

log = logging.getLogger(__name__)


class CustomShifterStep(cstp.customShifterMainStep):
    """
    This step loads a model file called "model.mb" from the asset path defined by the `paths` pre-step,
    and puts it in the rig hierarchy.
    """

    def setup(self) -> None:
        """
        Setting the name property makes the custom step accessible
        in later steps.

        i.e: Running  self.custom_step("{name}")  from steps ran after
             this one, will grant this step.
        """
        self.name = "skin_model"

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
        paths_step: PathsStep = self.custom_step("paths")

        mgear_rig: Rig = self.rig
        dev_build = mgear_rig.options["mode"] == 1

        data_path: Path = paths_step.rig_data_path
        skin_path: Path = data_path / "skin"
        if not skin_path.exists():
            raise RuntimeError(f"No skin folder found in {data_path}")

        geo_in_set: list[str] = cmds.sets("rig_geo_grp", query=True)  # type: ignore
        def_in_set = cmds.sets("rig_deformers_grp", query=True)
        def_joints = cmds.ls(def_in_set, type="joint")  # type: ignore

        def _fallback_skin(geometry: str):
            skin_geometry(def_joints, geometry)
            log.info(f"Default skinning bound {geometry} to {len(def_joints)} joint(s)")

        skin_and_apply_weights_from_directory(
            skin_path, geo_in_set, fallback_skinning=_fallback_skin
        )
        for geo in geo_in_set:
            # If this is a non dev build we also remove influences with 0 weights for performance
            if not dev_build:
                removed = remove_unused_influences(geo)
                if removed:
                    log.info(f"Removed {len(removed)} unused influences on {geo}")
