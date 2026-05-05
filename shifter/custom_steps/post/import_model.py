from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import mgear.shifter.custom_step as cstp
from maya import cmds

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
        self.name = "import_model"

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

        assets_path: Path = paths_step.rig_assets_path
        model_path: Path = assets_path / "model.mb"
        if not model_path.exists():
            raise RuntimeError(f"No model file found at {model_path}")
        log.info(f"Loading model file: {model_path}")
        imported_nodes: list[str] = cmds.file(
            str(model_path), i=True, defaultNamespace=True, returnNewNodes=True
        )  # type: ignore

        top_level_nodes: list[str] = cmds.ls(imported_nodes, assemblies=True)  # type: ignore
        if not top_level_nodes:
            raise RuntimeError("No transforms found in imported model!")

        # Case 1: exactly one root transform
        if len(top_level_nodes) == 1:
            top_level_node = top_level_nodes[0]
            if cmds.nodeType(top_level_node) == "transform":
                geo_grp = top_level_node
            else:
                geo_grp = cmds.group(top_level_node, name="geo", world=True)
            if geo_grp != "geo":
                geo_grp = cmds.rename(geo_grp)
        else:
            # Case 2: multiple top level transforms (we need to group them)
            geo_grp = cmds.group(top_level_nodes, name="geo", world=True)  # type: ignore

        # Keep in mind the mgear rig object's "model" is actually the root rig transform.
        cmds.parent(geo_grp, mgear_rig.model)
        cmds.reorder(geo_grp, front=True)
        cmds.reorder(geo_grp, relative=1)
        self.geo_group = geo_grp

        # Get the imported meshes
        meshes = cmds.listRelatives(geo_grp, allDescendents=True, type="mesh")
        mesh_transforms = (
            cmds.listRelatives(
                meshes,  # type: ignore
                parent=True,
                fullPath=True,
            )
            or []
        )
        # remove duplicates
        mesh_transforms: list[str] = list(set(mesh_transforms))
        # Put the geo in the set.
        cmds.sets(mesh_transforms, add="rig_geo_grp")  # type: ignore
