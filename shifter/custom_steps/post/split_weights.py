from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import mgear.shifter.custom_step as cstp
from maya import cmds

from yrig.skin.split import auto_split_weights

if TYPE_CHECKING:
    from mgear.shifter import Rig

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
        self.name = "split_weights"

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
        geo_in_set: list[str] = cmds.sets("rig_geo_grp", query=True)  # type: ignore
        auto_split_weights(geo_in_set)
