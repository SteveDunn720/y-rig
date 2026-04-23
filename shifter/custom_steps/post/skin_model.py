from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import mgear.shifter.custom_step as cstp
from maya import cmds

from yrig.build.progress import progress_step, progress_update
from yrig.name import get_short_name
from yrig.skin.core import remove_unused_influences, skin_mesh
from yrig.skin.ng import apply_ng_skin_weights, get_influences_from_ng_skin_weights

if TYPE_CHECKING:
    from mgear.shifter import Rig

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

        mgear_rig: Rig = self.mgear_run
        dev_build = True if mgear_rig.options["mode"] == 1 else False

        data_path: Path = paths_step.rig_data_path
        skin_path: Path = data_path / "skin"
        if not skin_path.exists():
            raise RuntimeError(f"No skin folder found in {data_path}")

        geo_in_set: list[str] = cmds.sets("rig_geo_grp", query=True)  # type: ignore
        def_in_set = cmds.sets("rig_deformers_grp", query=True)
        def_joints = cmds.ls(def_in_set, type="joint")  # type: ignore
        with progress_step("Skin Model"):
            total = len(geo_in_set)
            for i, geo in enumerate(geo_in_set):
                skin_filepath: Path = skin_path / f"{geo}.json"

                if skin_filepath.exists():
                    influence_paths = get_influences_from_ng_skin_weights(skin_filepath)
                    influence_names = [get_short_name(path) for path in influence_paths]
                    # Filter to joints that actually exist in scene
                    valid_influences = [j for j in influence_names if cmds.objExists(j)]
                    missing_influences = set(influence_names) - set(valid_influences)
                    if missing_influences:
                        log.warning(
                            f"[{geo}] Missing {len(missing_influences)} influence(s) that were defined in its skin file : {sorted(missing_influences)}"
                        )

                    # Only bind to joints specified in the skin file for final build
                    bind_joints = def_joints if dev_build else valid_influences
                    skin_mesh(bind_joints, geo)
                    log.info(f"Skinned {geo} to {len(bind_joints)} joint(s)")

                    apply_ng_skin_weights(skin_filepath, geo)
                    log.info(f"Loaded ng skin file for {geo}")
                else:
                    skin_mesh(def_joints, geo)
                    log.info(f"Default skinning bound {geo} to {len(def_joints)} joint(s)")

                # If this is a non dev build we also remove influences with 0 weights for performance
                if not dev_build:
                    removed = remove_unused_influences(geo)
                    if removed:
                        log.info(f"Removed {len(removed)} unused influences on {geo}")

                progress_update(i / total)
