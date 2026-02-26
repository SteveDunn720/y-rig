from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import mgear.shifter.custom_step as cstp
from maya import cmds

from yrig.skin.core import skin_mesh
from yrig.skin.ng import apply_ng_skin_weights

if TYPE_CHECKING:
    from ..pre.paths import CustomShifterStep as PathsStep

log = logging.getLogger(__name__)


class CustomShifterStep(cstp.customShifterMainStep):
    """
    This step loads a model file called "model.mb" from the asset path defined by the `paths` pre-step,
    and puts it in the rig hierarchy.
    """

    def setup(self):
        """
        Setting the name property makes the custom step accessible
        in later steps.

        i.e: Running  self.custom_step("{name}")  from steps ran after
             this one, will grant this step.
        """
        self.name = "skin_model"

    def run(self):
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

        data_path: Path = paths_step.rig_data_path
        skin_path: Path = data_path / "skin"
        if not skin_path.exists():
            raise RuntimeError(f"No skin folder found in {data_path}")

        geo_in_set: list[str] = cmds.sets("rig_geo_grp", query=True)  # type: ignore
        def_in_set = cmds.sets("rig_deformers_grp", query=True)
        def_joints = cmds.ls(def_in_set, type="joint")  # type: ignore
        for geo in geo_in_set:
            skin_mesh(def_joints, geo)
            log.info(f"Skinned {geo} to {len(def_joints)} joint(s)")
            skin_filepath: Path = skin_path / f"{geo}.json"
            if not skin_filepath.exists():
                geo_short_name = geo.rsplit("_", 1)[0]
                skin_filepath: Path = skin_path / f"{geo_short_name}.json"
                if not skin_filepath.exists():
                    continue
            apply_ng_skin_weights(skin_filepath, geo)
            log.info(f"Loaded ng skin file for {geo}")
