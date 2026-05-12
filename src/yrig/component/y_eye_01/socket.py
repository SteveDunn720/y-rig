from yrig import control
import enum
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


class Socket:
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

        # Ensure we are working with the shape node
        shapes = cmds.listRelatives(curve, shapes=True, fullPath=True) or []
        if shapes:
            working_curve = shapes[0]

        top_grp = create_transform(name=f"{descriptor}_spline_{self.side}_grp", parent=parent)

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

    def build_socket(self) -> None:
        self.major_controls = {}
        self.parent_controls = {}
        self.main_joints = {}
        major_guides = [
            "socket_inner_upper",
            "socket_mid_upper",
            "socket_outer_upper",
            "socket_inner_lower",
            "socket_mid_lower",
            "socket_outer_lower",
            "socket_inner_corner",
            "socket_outer_corner",
        ]

        for side in ["upper", "lower"]:
            self.parent_controls[f"{side}_ctrl"] = create_control(
                name=f"socket_{side}_{self.side}",
                parent=self.main_ctrl,
                transform=self.guides[f"socket_mid_{side}"],
                size=self.control_size / 4,
                control_shape="round_square",
                direction="z",
                dimensions=(1, 0.2, 0.2),
            )

        for i, guide in enumerate(major_guides):
            if i in [0, 1, 2]:
                parent = self.parent_controls["upper_ctrl"]
            elif i in [3, 4, 5]:
                parent = self.parent_controls["lower_ctrl"]
            else:
                parent = self.main_ctrl
            self.major_controls[f"{guide}_ctrl"] = create_control(
                name=f"{guide}_{self.side}",
                parent=parent,
                transform=self.guides[f"{guide}"],
                size=self.control_size / 8,
                control_shape="circle",
                direction="z",
            )
            self.main_joints[f"{guide}_jnt"] = create_joint(
                name=f"{guide}_{self.side}",
                transform=self.major_controls[f"{guide}_ctrl"].transform,
                parent=self.joint_parent,
            )

        self.upper_driver_controls = [
            self.main_joints[f"socket_inner_corner_jnt"],
            self.main_joints[f"socket_inner_upper_jnt"],
            self.main_joints[f"socket_mid_upper_jnt"],
            self.main_joints[f"socket_outer_upper_jnt"],
            self.main_joints[f"socket_outer_corner_jnt"],
        ]
        self.lower_driver_controls = [
            self.main_joints[f"socket_inner_corner_jnt"],
            self.main_joints[f"socket_inner_lower_jnt"],
            self.main_joints[f"socket_mid_lower_jnt"],
            self.main_joints[f"socket_outer_lower_jnt"],
            self.main_joints[f"socket_outer_corner_jnt"],
        ]

        tag_for_weight_split(
            influence=self.lower_driver_controls[2],  # <-- your SOURCE joint (must already exist)
            split_influences=self.lower_driver_controls,  # <-- the ones you just created
        )

        tag_for_weight_split(
            influence=self.upper_driver_controls[2],  # <-- your SOURCE joint (must already exist)
            split_influences=self.upper_driver_controls,  # <-- the ones you just created
        )

        #######
        # Matix Spline Eyelids
        #######

        """self.upper_spline = self.curve_to_matrix_spline(
            parent=self.control_grp,
            curve=self.guides["socket_upper_curve"],
            descriptor="upper_socket",
            driver_list=self.upper_driver_controls,
            ignore_handles=True,
        )

        self.lower_spline = self.curve_to_matrix_spline(
            parent=self.control_grp,
            curve=self.guides["socket_lower_curve"],
            descriptor="lower_socket",
            driver_list=self.lower_driver_controls,
            ignore_handles=True,
        )"""

        """cmds.connectAttr(f"{self.main_ctrl}.sub_socket", f"{self.upper_spline}.visibility")
        cmds.connectAttr(f"{self.main_ctrl}.sub_socket", f"{self.lower_spline}.visibility")"""
