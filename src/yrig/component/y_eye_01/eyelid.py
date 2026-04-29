from yrig.control.core import Control
from typing import Any

import maya.cmds as cmds
from yrig.control import create_control

# from yrig.joint import create_joint
from yrig.transform import create_transform
from maya.api.OpenMaya import MMatrix, MTransformationMatrix, MVector, MEulerRotation, MSpace
from yrig.transform.utils import get_position
import math

from yrig.maya_api.node import (
    PlusMinusAverage,
    Condition,
    MultMatrixNode,
    DecomposeMatrixNode,
    MultiplyDivideNode,
)


class Eyelid:
    def __init__(self, side="L", guides={}, control_size=1, main_ctrl: str = "", parent: str = ""):
        self.side = side
        self.guides = guides
        self.main_ctrl = main_ctrl
        self.control_size = control_size
        self.parent = parent

    # -------------------
    # Helper Functions
    # -------------------
    def convert_to_matrix(
        self,
        pos=(0, 0, 0),
        rot=(0, 0, 0),
        scale=(1, 1, 1),
    ) -> MMatrix:
        """
        Build an MMatrix from translation, rotation, and scale.
        """

        m = MTransformationMatrix()

        # Translation
        m.setTranslation(MVector(*pos), MSpace.kWorld)

        # Rotation (Euler degrees → radians internally handled by API)
        euler = MEulerRotation(
            math.radians(rot[0]),
            math.radians(rot[1]),
            math.radians(rot[2]),
        )
        m.setRotation(euler)

        # Scale
        m.setScale(scale, MSpace.kWorld)

        return m.asMatrix()

    def get_flat_y_aim_rotation(self, source: str, target: str) -> float:
        """
        Returns Y-axis rotation (degrees) from source → target,
        ignoring Y height (XZ plane only).
        """

        p1: Any = get_position(transform=source)
        p2: Any = get_position(transform=target)

        # Flatten Y
        dx = p2.x - p1.x
        dz = p2.z - p1.z

        # Angle in radians
        angle = math.atan2(dx, dz)

        # Convert to degrees
        return math.degrees(angle)

    def soft_colide(
        self,
        Upper_driver: str,
        Lower_driver: str,
        Upper_driven: str,
        Lower_driven: str,
        parent: str,
        push=0.5,
        rot_mult: float = -50,
    ):

        ctrl_list = [Lower_driver, Upper_driver]

        out_matrix = []

        # shared logic to check how close our two drivers are

        pma_calc = PlusMinusAverage(name=f"{Upper_driver}_{Lower_driver}_PMA")
        pma_calc.operation.set(2)

        condition = Condition(name=f"{Upper_driver}_{Lower_driver}_COND")
        condition.operation.set(2)
        condition.color_if_false.set((0, 0, 0))

        pma_calc.output_1d.connect_to(condition.color_if_true.x)
        pma_calc.output_1d.connect_to(condition.first_term)

        # cmds.connectAttr(f"{pma_calc}.output1D", f"{condition}.colorIfTrueR")
        # cmds.connectAttr(f"{pma_calc}.output1D", f"{condition}.firstTerm")

        rot_md = MultiplyDivideNode(name=f"{Upper_driver}_{Lower_driver}_MD")

        for ctrl in ctrl_list:
            cmds.addAttr(ctrl, longName="push", at="double", dv=push, k=True)  # type:ignore
            cmds.addAttr(ctrl, longName="rot_mult_DEV", at="double", dv=rot_mult, k=True)  # type:ignore
            mult_matrix = MultMatrixNode(name=f"{ctrl}_MM")
            dec_matrix = DecomposeMatrixNode(name=f"{ctrl}_DM")

            # Connect world matrix → multMatrix
            mult_matrix.matrix_in[0].connect_from(f"{ctrl}.worldMatrix[0]")
            mult_matrix.matrix_in[1].connect_from(f"{parent}.worldInverseMatrix[0]")

            # multMatrix → decomposeMatrix
            dec_matrix.input_matrix.connect_from(mult_matrix.matrix_sum)

            # Connect output Y into PMA
            if ctrl == ctrl_list[0]:
                dec_matrix.output_translate.y.connect_to(pma_calc.input_1d[0])
                cmds.connectAttr(f"{ctrl}.rot_mult_DEV", f"{rot_md.input2.x}")
                cmds.connectAttr(f"{rot_md.output.x}", f"{Lower_driven}.rotateX")

            else:
                dec_matrix.output_translate.y.connect_to(pma_calc.input_1d[1])
                cmds.connectAttr(f"{ctrl}.rot_mult_DEV", f"{rot_md.input2.y}")
                cmds.connectAttr(f"{rot_md.output.y}", f"{Upper_driven}.rotateX")

            out_matrix.append(dec_matrix)

            # push logic

            # -------------------------
            # push multiplyDivide
            # -------------------------
            push_mult = MultiplyDivideNode(name=f"{ctrl}_MD")

            push_mult.input2.x.set(0.5 if ctrl == ctrl_list[0] else -0.5)
            push_mult.operation.set(1)  # assuming multiply

            condition.out_color.x.connect_to(push_mult.input1.x)

            # -------------------------
            # plusMinusAverage driver
            # -------------------------
            pma_drive = PlusMinusAverage(name=f"{ctrl}_PMA")
            pma_drive.operation.set(2)

            dec_matrix.output_translate.y.connect_to(pma_drive.input_1d[0])
            push_mult.output.x.connect_to(pma_drive.input_1d[1])

    def build_blink(self, z_offset: float = 1, x_offset: float = 1):
        ### get middle x pos for the blink

        upper_pos: Any = get_position(transform=self.guides["eyelid_upper"])
        lower_pos: Any = get_position(transform=self.guides["eyelid_upper"])

        blink_x: float = (upper_pos.x + lower_pos.x) / 2
        blink_z: float = (upper_pos.z + lower_pos.z) / 2 + z_offset

        self.main_blink_controls = []
        self.sub_blink_controls: dict[str, Control] = {}

        sub_transform_grp = create_transform(
            name="sub_blink_offset_matrix_drivers",
            parent=self.main_ctrl,
            transform=self.guides["center_piv"],
        )

        print(sub_transform_grp)

        # pper_matrix: Any = self.convert_to_matrix(pos=(blink_x, upper_pos.y, blink_z))
        # lower_matrix: Any = self.convert_to_matrix(pos=(blink_x, lower_pos.y, blink_z))

        for side in ["upper", "lower"]:
            blink_matrix: Any = self.convert_to_matrix(pos=(blink_x, upper_pos.y, blink_z))
            blink_ctrl = create_control(
                name=f"{side}_blink_{self.side}",
                parent=self.main_ctrl,
                transform=blink_matrix,
                size=self.control_size,
                control_shape=f"{side}_semi_circle",
                direction="z",
            )
            self.main_blink_controls.append[blink_ctrl]  # type:ignore

        for sub_blink in ["inner", "mid", "outer"]:
            driven_grps_list: list[str] = []
            for side in ["upper", "lower"]:
                # setting up mods

                side_mod = 1 if self.side == "L" else -1

                if sub_blink == "inner":
                    mod = -1
                elif sub_blink == "mid":
                    mod = 0
                else:
                    mod = -1

                new_matrix: Any = self.convert_to_matrix(
                    pos=(blink_x + (mod * side_mod), upper_pos.y, blink_z)
                )

                # building sub controls

                self.sub_blink_controls[f"{sub_blink}_{side}_blink_ctrl"] = create_control(
                    name=f"{sub_blink}_{side}_blink_{self.side}",
                    parent=self.main_ctrl,
                    transform=new_matrix,
                    size=self.control_size,
                    control_shape="sphere",
                    direction="z",
                )

                self.sub_blink_offset = create_transform(
                    name=f"{sub_blink}_{side}_blink_SDK",
                    parent=self.sub_blink_controls[f"{sub_blink}_{side}_blink_ctrl"].offset,
                    transform=self.guides["center_piv"],
                )

                cmds.parent(
                    self.sub_blink_controls[f"{sub_blink}_{side}_blink_ctrl"].transform,
                    self.sub_blink_offset,
                )

                # setting up blink driver groups

                aim: float = self.get_flat_y_aim_rotation(
                    source=self.guides["center_piv"],
                    target=self.guides[f"eyelid_{sub_blink}_{side}"],
                )

                driver_offset: str = create_transform(
                    name=f"{sub_blink}_{side}_blink_offset",
                    parent=self.main_ctrl,
                    transform=self.guides["center_piv"],
                )

                driver_driven: str = create_transform(
                    name=f"{sub_blink}_{side}_blink_driven",
                    parent=driver_offset,
                    transform=self.guides["center_piv"],
                )

                driven_grps_list.append(driver_driven)

                driver_driver: str = create_transform(
                    name=f"{sub_blink}_{side}_blink_driver",
                    parent=driver_driven,
                    transform=self.guides["center_piv"],
                )

                print(driver_driver)

                cmds.setAttr(f"{driver_offset}.rotateY", aim)  # type:ignore

                driven_transform = create_transform(
                    name=f"{sub_blink}_{side}_blink_offset",
                    parent=self.main_ctrl,
                    transform=self.guides[f"eyelid_{sub_blink}_{side}"],
                )

                # temp visualization will remove later
                sphere = cmds.polySphere(name="mySphere")[0]  # type:ignore
                cmds.delete(cmds.parentConstraint(driven_transform, sphere))  # type:ignore
                cmds.parent(sphere, driven_transform)  # type:ignore

            self.soft_colide(
                Upper_driver=self.sub_blink_controls[f"{sub_blink}_upper_blink_ctrl"].transform,
                Lower_driver=self.sub_blink_controls[f"{sub_blink}_lower_blink_ctrl"].transform,
                Upper_driven=driven_grps_list[0],
                Lower_driven=driven_grps_list[0],
                parent=self.main_ctrl,
                push=0.5,
            )
