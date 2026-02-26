from __future__ import annotations

import logging
from pathlib import Path

import mgear.shifter.custom_step as cstp

from yrig.build.context import get_asset_root

log = logging.getLogger(__name__)


class CustomShifterStep(cstp.customShifterMainStep):
    """
    This step gives the needed metadata and path information for later steps like loading the model, applying skin weights, etc.
    """

    def setup(self):
        """
        Setting the name property makes the custom step accessible
        in later steps.

        i.e: Running  self.custom_step("{name}")  from steps ran after
             this one, will grant this step.
        """
        self.name = "paths"

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
        asset_root = get_asset_root()
        self.rig_root_path: Path
        if asset_root is None:
            self.rig_root_path = Path(__file__).parents[1]
            log.warning(
                f"No asset root path set, assuming root is {self.rig_root_path} based on the file location of this step."
            )
        else:
            self.rig_root_path = asset_root
        self.rig_data_path = self.rig_root_path / "data"
        self.rig_assets_path = self.rig_root_path / "assets"
