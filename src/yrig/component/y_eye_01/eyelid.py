from mgear.utilbits.xplorer import _maya_icon_cache
import mailbox
from numpy import iterable
from yrig.control.core import Control
from typing import Any, Literal

import maya.cmds as cmds
from yrig.control import create_control
from yrig.joint import create_joint

from yrig.transform import create_transform
from maya.api.OpenMaya import MMatrix, MTransformationMatrix, MVector, MEulerRotation, MSpace
from yrig.transform.utils import get_position
import math
from yrig.transform.matrix import matrix_constraint
from yrig.skin.split.tag import tag_for_weight_split

from yrig.maya_api.node import (
    PlusMinusAverageNode,
    ConditionNode,
    MultMatrixNode,
    DecomposeMatrixNode,
    MultiplyDivideNode,
    AddDLNode,
)

from yrig.spline.matrix_spline.build import matrix_spline_from_transforms


class Eyelid:
    def __init__(
        self,
        side: str = "L",
        guides: dict = {},
        control_size: float = 1.0,
        main_ctrl: str = "",
        parent: str = "",
        joint_parent: str = "",
        componet_grp: str = "",
        control_grp: str = "",
    ) -> None:
        self.side = side
        self.guides = guides
        self.main_ctrl = main_ctrl
        self.control_size = control_size
        self.parent = parent
        self.joint_parent = joint_parent
        self.componet_grp = componet_grp
        self.control_grp = control_grp

    # -------------------
    # Helper Functions
    # -------------------
    def convert_to_matrix(
        self,
        pos: tuple[float, float, float] = (0, 0, 0),
        rot: tuple[float, float, float] = (0, 0, 0),
        scale: tuple[float, float, float] = (1, 1, 1),
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

    def curve_to_matrix_spline(
        self,
        parent: str,
        curve: str,
        descriptor: str,
        driver_list: list,
        rebuild: bool = False,
        cv_count: int = 10,
        ignore_handles: bool = False,
    ) -> str:
        """
        Returns worldspace positions of CVs on a curve.

        Args:
            curve (str): Name of the curve transform or shape.
            rebuild (bool): If True, duplicate and rebuild curve.
            cv_count (int): Number of CVs if rebuilding.
            ignore_handles (bool): If True, skip 2nd and 2nd-to-last CV.

        Returns:
            list of tuples: [(x, y, z), ...]
        """

        temp_curve = None
        working_curve = curve

        top_grp = create_transform(name=f"{descriptor}_spline_{self.side}_grp", parent=parent)

        # Ensure we are working with the shape node
        shapes = cmds.listRelatives(curve, shapes=True, fullPath=True) or []
        if shapes:
            working_curve = shapes[0]

        # Optional rebuild
        if rebuild:
            temp_curve = cmds.duplicate(curve, name=curve + "_tempRebuild")[0]

            cmds.rebuildCurve(
                temp_curve,
                ch=False,  # type:ignore
                rpo=True,  # type:ignore
                rt=0,  # type:ignore
                end=1,  # type:ignore
                kr=0,  # type:ignore
                kcp=False,  # type:ignore
                kep=True,  # type:ignore
                kt=False,  # type:ignore
                s=cv_count - 1,  # type:ignore
                d=3,  # type:ignore
            )

            # Get shape of rebuilt curve
            shapes = cmds.listRelatives(temp_curve, shapes=True, fullPath=True) or []
            if shapes:
                working_curve = shapes[0]
            else:
                working_curve = temp_curve

        # Get CV count
        spans = cmds.getAttr(working_curve + ".spans")
        degree = cmds.getAttr(working_curve + ".degree")
        cv_total = spans + degree

        indices = list(range(cv_total))

        # Ignore handles if requested
        if ignore_handles and cv_total > 3:
            indices = [i for i in indices if i not in (1, cv_total - 2)]

        self.sub_eyelid_controls = []
        self.sub_eyelid_joints = []
        sub_eyelid_offsets = []
        for i in indices:  # descriptor
            cv = f"{working_curve}.cv[{i}]"

            # Get CV position
            pos = get_position(cv)

            # Create temp transform
            temp = cmds.group(empty=True, name=f"{curve}_tempCv_{i}#")
            cmds.xform(temp, worldSpace=True, translation=(pos.x, pos.y, pos.z))

            sub_ctrl = create_control(
                name=f"{descriptor}_{i}_{self.side}",
                parent=top_grp,
                transform=temp,
                size=self.control_size / 10,
                control_shape="circle",
                direction="z",
            )
            sub_jnt = create_joint(
                name=f"{descriptor}_{i}_{self.side}",
                parent=self.joint_parent,
                transform=sub_ctrl.transform,
            )

            self.sub_eyelid_controls.append(sub_ctrl)
            self.sub_eyelid_joints.append(sub_jnt)
            sub_eyelid_offsets.append(sub_ctrl.offset)

            cmds.delete(temp)

        # Cleanup
        if temp_curve and cmds.objExists(temp_curve):
            cmds.delete(temp_curve)

        tag_for_weight_split(
            influence=self.sub_eyelid_joints[0],  # <-- your SOURCE joint (must already exist)
            split_influences=self.sub_eyelid_joints,  # <-- the ones you just created
        )

        matrix_spline_from_transforms(
            name=f"{self.side}_{descriptor}",
            pinned_transforms=sub_eyelid_offsets,
            cv_transforms=driver_list,
            parent=self.componet_grp,
            degree=2,
        )

        return top_grp

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
        push: float = 0.5,
        rot_mult: float = -50,
    ) -> None:

        ctrl_list = [Lower_driver, Upper_driver]

        out_matrix = []

        # shared logic to check how close our two drivers are

        pma_calc = PlusMinusAverageNode(name=f"{Upper_driver}_{Lower_driver}_PMA")
        pma_calc.operation.set(2)

        condition = ConditionNode(name=f"{Upper_driver}_{Lower_driver}_COND")
        condition.operation.set(2)
        condition.color_if_false.set((0, 0, 0))

        pma_calc.output_1d.connect_to(condition.color_if_true.r)
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

            condition.out_color.r.connect_to(push_mult.input1.x)

            # -------------------------
            # PlusMinusAverageNode driver
            # -------------------------
            pma_drive = PlusMinusAverageNode(name=f"{ctrl}_PMA")
            pma_drive.operation.set(2)

            dec_matrix.output_translate.y.connect_to(pma_drive.input_1d[0])
            push_mult.output.x.connect_to(pma_drive.input_1d[1])

            if ctrl == ctrl_list[0]:
                cmds.connectAttr(f"{pma_drive.output_1d}", f"{rot_md.input1.x}")
            else:
                cmds.connectAttr(f"{pma_drive.output_1d}", f"{rot_md.input1.y}")

    def build_blink(
        self,
        z_offset: float = 1,
        x_offset: float = 1,
    ) -> None:
        ### get middle x pos for the blink

        pos_list = []

        upper_pos: Any = get_position(transform=self.guides["eyelid_mid_upper"])
        lower_pos: Any = get_position(transform=self.guides["eyelid_mid_lower"])

        pos_list.append(upper_pos)
        pos_list.append(lower_pos)

        blink_x: float = (upper_pos.x + lower_pos.x) / 2
        blink_y: float = (upper_pos.y + lower_pos.y) / 2
        blink_z: float = (upper_pos.z + lower_pos.z) / 2 + z_offset

        self.main_blink_controls = []
        self.sub_blink_controls: dict[str, Control] = {}
        self.sub_blink_offsets = []
        self.main_eyelid_controls: dict[str, Control] = {}
        self.blink_drivers = {}
        self.main_eyelid_joints: dict[str, str] = {}

        #######
        # Set up look follow
        #######

        self.look_offset = create_transform(
            name=f"{self.side}_look_offset",
            parent=self.main_ctrl,
            transform=self.guides["center_piv"],
        )

        #######
        # Sub Blink Set up // Main Eyelid Set up
        #######
        twist_grps = []
        for i, side in enumerate(["upper", "lower"]):
            sub_transform_grp = create_transform(
                name=f"{self.side}_{side}_sub_blink_offset_matrix_drivers",
                parent=self.look_offset,
                transform=self.guides["center_piv"],
            )
            twist_grps.append(sub_transform_grp)

        for sub_blink in ["corner_inner", "inner", "mid", "outer", "corner_outer"]:
            driven_grps_list: list[str] = []
            driver_grps_list: list[str] = []

            p1 = get_position(transform=self.guides[f"eyelid_{sub_blink}_upper"])
            p2 = get_position(transform=self.guides[f"eyelid_{sub_blink}_lower"])

            y_offset = (MVector(p2.x, p2.y, p2.z) - MVector(p1.x, p1.y, p1.z)).length() / 10
            for i, side in enumerate[str](["upper", "lower"]):
                # setting up mods

                up_mod: Literal[1, -1] = 1 if side == "upper" else -1

                side_mod: Literal[1, -1] = 1 if self.side == "L" else -1

                if sub_blink == "inner":
                    mod = -1
                elif sub_blink == "mid":
                    mod = 0
                else:
                    mod = 1

                new_matrix: Any = self.convert_to_matrix(
                    pos=(
                        blink_x + (mod * side_mod * x_offset),
                        blink_y + (up_mod * y_offset),
                        blink_z,
                    )
                )

                # building sub controls

                self.sub_blink_controls[f"{sub_blink}_{side}_blink_ctrl"] = create_control(
                    name=f"{sub_blink}_{side}_blink_{self.side}",
                    parent=self.main_ctrl,
                    transform=new_matrix,
                    size=self.control_size / 10,
                    control_shape="sphere",
                    direction="z",
                )

                self.sub_blink_offsets.append(
                    self.sub_blink_controls[f"{sub_blink}_{side}_blink_ctrl"].transform
                )

                self.sub_blink_controls[f"{sub_blink}_{side}_blink_ctrl"].SDKGRP = create_transform(  # type:ignore
                    name=f"{sub_blink}_{side}_blink_SDK",
                    parent=self.sub_blink_controls[f"{sub_blink}_{side}_blink_ctrl"].offset,
                    transform=new_matrix,
                )

                self.sub_blink_offset = self.sub_blink_controls[
                    f"{sub_blink}_{side}_blink_ctrl"
                ].SDKGRP  # type:ignore

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
                    parent=twist_grps[i],
                    transform=self.guides["center_piv"],
                )

                driver_driven: str = create_transform(
                    name=f"{sub_blink}_{side}_blink_driven",
                    parent=driver_offset,
                    transform=self.guides["center_piv"],
                )

                self.blink_drivers[f"{sub_blink}_{side}_blink_ctrl"] = driver_driven

                driven_grps_list.append(driver_driven)

                driver_driver: str = create_transform(
                    name=f"{sub_blink}_{side}_blink_driver",
                    parent=driver_driven,
                    transform=self.guides["center_piv"],
                )

                driver_grps_list.append(driver_driver)

                # cmds.setAttr(f"{driver_offset}.rotateY", aim * -1)

                self.main_eyelid_controls[f"{sub_blink}_{side}_eyelid_ctrl"] = create_control(
                    name=f"{sub_blink}_{side}_eyelid_{self.side}",
                    parent=self.main_ctrl,
                    transform=self.guides[f"eyelid_{sub_blink}_{side}"],
                    size=self.control_size / 4,
                    control_shape="sphere",
                    direction="z",
                )

                self.main_eyelid_joints[f"{sub_blink}_{side}_eyelid_jnt"] = create_joint(
                    name=f"{sub_blink}_{side}_eyelid_{self.side}",
                    transform=self.main_eyelid_controls[
                        f"{sub_blink}_{side}_eyelid_ctrl"
                    ].transform,
                    parent=self.joint_parent,
                )

                ##### Adding x translate control funtionality to the controls

                x_md = MultiplyDivideNode(name=f"{sub_blink}_{side}_{self.side}_L")

                x_md.input1.x.connect_from(
                    f"{self.sub_blink_controls[f'{sub_blink}_{side}_blink_ctrl'].transform}.translateX"
                )
                x_md.output.x.connect_to(f"{driver_driven}.rotateZ")
                x_md.input2.x.set(-30)

            self.soft_colide(
                Upper_driver=self.sub_blink_controls[f"{sub_blink}_upper_blink_ctrl"].transform,
                Lower_driver=self.sub_blink_controls[f"{sub_blink}_lower_blink_ctrl"].transform,
                Upper_driven=driven_grps_list[0],
                Lower_driven=driven_grps_list[1],
                parent=self.main_ctrl,
                push=0.5,
            )

            matrix_constraint(
                source_transform=driver_grps_list[0],
                constrain_transform=self.main_eyelid_controls[
                    f"{sub_blink}_upper_eyelid_ctrl"
                ].offset,
                keep_offset=True,
            )
            matrix_constraint(
                driver_grps_list[1],
                self.main_eyelid_controls[f"{sub_blink}_lower_eyelid_ctrl"].offset,
                keep_offset=True,
            )

        ##########
        # Main Control Behavior
        ##########
        for i, side in enumerate[str](["upper", "lower"]):
            mod = "high" if side == "upper" else "low"
            blink_matrix: Any = self.convert_to_matrix(pos=(blink_x, blink_y, blink_z))
            blink_ctrl = create_control(
                name=f"{side}_blink_{self.side}",
                parent=self.main_ctrl,
                transform=blink_matrix,
                size=self.control_size,
                control_shape=f"{mod}_semi_circle",
                direction="z",
            )
            twist_MD = MultiplyDivideNode(name=f"{self.side}_{side}_twist_DM")
            cmds.connectAttr(f"{blink_ctrl.transform}.translateX", f"{twist_MD.input1.x}")
            cmds.setAttr(f"{twist_MD.input2.x}", 15)  # type:ignore

            self.main_blink_controls.append(blink_ctrl)
            cmds.connectAttr(f"{twist_MD.output.x}", f"{twist_grps[i]}.rotateY")

            cmds.connectAttr(
                f"{blink_ctrl.transform}.translateY",
                f"{self.sub_blink_controls[f'mid_{side}_blink_ctrl'].SDKGRP}.translateY",  # type:ignore
            )
            mod_values = [-2, -1, 1, 2]
            for i, sub in enumerate(["corner_inner", "inner", "outer", "corner_outer"]):
                mod: int = mod_values[i]
                input_mult = MultiplyDivideNode(name=f"{self.side}_{side}_{sub}_input_MD")
                addDL_node: AddDLNode = AddDLNode(name=f"{self.side}_{side}_{sub}_ADL")
                input_mult.input1.x.connect_from(f"{blink_ctrl.transform}.rotateZ")
                cmds.setAttr(f"{input_mult.input2.x}", 0.03 * mod)  # type:ignore
                cmds.connectAttr(f"{blink_ctrl.transform}.translateY", f"{addDL_node.input_1}")
                cmds.connectAttr(f"{input_mult.output.x}", f"{addDL_node.input_2}")
                cmds.connectAttr(
                    f"{addDL_node.output}",
                    f"{self.sub_blink_controls[f'{sub}_{side}_blink_ctrl'].SDKGRP}.translateY",  # type:ignore
                )

        #######
        # Corner Controls
        #######
        corner_controls = []
        for side in ["upper", "lower"]:
            for sub in ["inner", "outer"]:
                self.main_eyelid_controls[f"{sub}_{side}_corner_eyelid_ctrl"] = create_control(
                    name=f"{sub}_{side}_corner_eyelid_{self.side}",
                    parent=self.look_offset,
                    transform=self.guides[f"eyelid_{sub}_corner"],
                    size=self.control_size / 4,
                    control_shape="sphere",
                    direction="z",
                )

                self.main_eyelid_joints[f"{sub}_{side}_corner_eyelid_jnt"] = create_joint(
                    name=f"{sub}_{side}_corner_eyelid_{self.side}",
                    transform=self.main_eyelid_controls[
                        f"{sub}_{side}_corner_eyelid_ctrl"
                    ].transform,
                    parent=self.joint_parent,
                )

                matrix_constraint(
                    self.blink_drivers[f"{sub}_{side}_blink_ctrl"],
                    self.main_eyelid_controls[f"{sub}_{side}_corner_eyelid_ctrl"].offset,
                    translate=False,
                    rotate=True,
                    keep_offset=True,
                    scale=False,
                    shear=False,
                )

                """matrix_constraint(
                    self.main_eyelid_controls[f"corner_{sub}_{side}_eyelid_ctrl"].transform,
                    self.main_eyelid_controls[f"{sub}_{side}_corner_eyelid_ctrl"].offset,
                    translate=True,
                    rotate=False,
                    keep_offset=True,
                    scale=False,
                    shear=False,
                )"""

                cmds.pointConstraint(
                    self.main_eyelid_controls[f"corner_{sub}_{side}_eyelid_ctrl"].transform,
                    self.main_eyelid_controls[f"{sub}_{side}_corner_eyelid_ctrl"].offset,
                    maintainOffset=True,
                )
                cmds.pointConstraint(
                    self.main_ctrl,
                    self.main_eyelid_controls[f"{sub}_{side}_corner_eyelid_ctrl"].offset,
                    maintainOffset=True,
                )

                # blend_md = MultiplyDivideNode(name=f"{sub}_{side}_corner_eyelid_MD")
                """blend_ADL = AddDLNode(name=f"{sub}_{side}_corner_eyelid_ADL")
                blend_ADL.output.connect_to(
                    f"{self.main_eyelid_controls[f'{sub}_{side}_corner_eyelid_ctrl']}.rotateX"
                )
                blend_ADL.input_1.connect_from(
                    f"{self.blink_drivers[f'{sub}_{side}_blink_ctrl']}.rotateX"
                )
                offset_value = blend_ADL.input_1.get()
                blend_ADL.input_2.set(offset_value)"""
        ## corner_inner
        """self.upper_driver_controls = [
            self.main_eyelid_controls[f"inner_upper_corner_eyelid_ctrl"],
            self.main_eyelid_controls[f"corner_inner_upper_eyelid_ctrl"],
            self.main_eyelid_controls[f"inner_upper_eyelid_ctrl"],
            self.main_eyelid_controls[f"mid_upper_eyelid_ctrl"],
            self.main_eyelid_controls[f"outer_upper_eyelid_ctrl"],
            self.main_eyelid_controls[f"corner_outer_upper_eyelid_ctrl"],
            self.main_eyelid_controls[f"outer_upper_corner_eyelid_ctrl"],
        ]
        self.lower_driver_controls = [
            self.main_eyelid_controls[f"inner_lower_corner_eyelid_ctrl"],
            self.main_eyelid_controls[f"corner_inner_lower_eyelid_ctrl"],
            self.main_eyelid_controls[f"inner_lower_eyelid_ctrl"],
            self.main_eyelid_controls[f"mid_lower_eyelid_ctrl"],
            self.main_eyelid_controls[f"outer_lower_eyelid_ctrl"],
            self.main_eyelid_controls[f"corner_outer_lower_eyelid_ctrl"],
            self.main_eyelid_controls[f"outer_lower_corner_eyelid_ctrl"],
        ]

        #######
        # Matix Spline Eyelids
        #######

        self.upper_spline = self.curve_to_matrix_spline(
            parent=self.control_grp,
            curve=self.guides["eyelid_upper_curve"],
            descriptor="upper_eyelid",
            driver_list=self.upper_driver_controls,
            ignore_handles=True,
        )

        self.lower_spline = self.curve_to_matrix_spline(
            parent=self.control_grp,
            curve=self.guides["eyelid_lower_curve"],
            descriptor="lower_eyelid",
            driver_list=self.lower_driver_controls,
            ignore_handles=True,
        )"""

        self.upper_driver_joint = [
            self.main_eyelid_joints[f"inner_upper_corner_eyelid_jnt"],
            self.main_eyelid_joints[f"corner_inner_upper_eyelid_jnt"],
            self.main_eyelid_joints[f"inner_upper_eyelid_jnt"],
            self.main_eyelid_joints[f"mid_upper_eyelid_jnt"],
            self.main_eyelid_joints[f"outer_upper_eyelid_jnt"],
            self.main_eyelid_joints[f"corner_outer_upper_eyelid_jnt"],
            self.main_eyelid_joints[f"outer_upper_corner_eyelid_jnt"],
        ]
        self.lower_driver_joint = [
            self.main_eyelid_joints[f"inner_lower_corner_eyelid_jnt"],
            self.main_eyelid_joints[f"corner_inner_lower_eyelid_jnt"],
            self.main_eyelid_joints[f"inner_lower_eyelid_jnt"],
            self.main_eyelid_joints[f"mid_lower_eyelid_jnt"],
            self.main_eyelid_joints[f"outer_lower_eyelid_jnt"],
            self.main_eyelid_joints[f"corner_outer_lower_eyelid_jnt"],
            self.main_eyelid_joints[f"outer_lower_corner_eyelid_jnt"],
        ]

        tag_for_weight_split(
            influence=self.lower_driver_joint[0],  # <-- your SOURCE joint (must already exist)
            split_influences=self.lower_driver_joint,  # <-- the ones you just created
        )

        tag_for_weight_split(
            influence=self.upper_driver_joint[0],  # <-- your SOURCE joint (must already exist)
            split_influences=self.upper_driver_joint,  # <-- the ones you just created
        )

        cmds.addAttr(
            self.main_ctrl,
            longName="eyelid_controls",
            attributeType="enum",
            enumName="-------------",
            keyable=True,
        )

        for vis_attr in ["sub_blink", "sub_eyelid", "sub_socket"]:
            cmds.addAttr(
                self.main_ctrl,
                longName=vis_attr,
                attributeType="bool",
                defaultValue=False,
                keyable=True,
            )

            for control in self.main_blink_controls:
                cmds.addAttr(
                    f"{control.transform}", longName=vis_attr, proxy=f"{self.main_ctrl}.{vis_attr}"
                )

        for control in self.sub_blink_offsets:
            cmds.connectAttr(f"{self.main_ctrl}.sub_blink", f"{control}.visibility")
            cmds.addAttr(
                f"{control}",
                longName="sub_blink",
                proxy=f"{self.main_ctrl}.sub_blink",
            )

        # cmds.connectAttr(f"{self.main_ctrl}.sub_eyelid", f"{self.upper_spline}.visibility")
        # cmds.connectAttr(f"{self.main_ctrl}.sub_eyelid", f"{self.lower_spline}.visibility")
