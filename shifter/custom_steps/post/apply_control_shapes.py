from pathlib import Path
from typing import TYPE_CHECKING

import mgear.shifter.custom_step as cstp

from yrig.control.serialize import apply_control_shapes_file

if TYPE_CHECKING:
    from ..pre.paths import CustomShifterStep as PathsStep


class CustomShifterStep(cstp.customShifterMainStep):
    """Custom Step description"""

    def setup(self):
        """
        Setting the name property makes the custom step accessible
        in later steps.

        i.e: Running  self.custom_step("apply_control_shapes")  from steps ran after
             this one, will grant this step.
        """
        self.name = "apply_control_shapes"

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
        control_shapes_path: Path = data_path / "control_shapes.json"
        apply_control_shapes_file(control_shapes_path)
        return
