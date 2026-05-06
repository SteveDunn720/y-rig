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
import math


class Eyeball:
    def __init__(
        self,
        side: str = "L",
        guides: dict = {},
        control_size: float = 1.0,
        main_ctrl: str = "",
        parent: str = "",
        joint_parent: str = "",
    ) -> None:
        self.side = side
        self.guides = guides
        self.main_ctrl = main_ctrl
        self.control_size = control_size
        self.parent = parent
        self.joint_parent = joint_parent

    # -------------------
    # Helper Functions
    # -------------------

    def get_nurbs_surface_radius(self, obj: str) -> float:
        """
        Returns the radius of a NURBS circle.

        Args:
            obj (str): Transform of the NURBS circle

        Returns:
            float: radius
        """

        bbox: list[int | float] = cmds.exactWorldBoundingBox(obj)

        x: int | float = bbox[3] - bbox[0]
        y: int | float = bbox[4] - bbox[1]
        z: int | float = bbox[5] - bbox[2]

        return max(x, y, z) * 0.5

    def compare_radius_and_angle(self, obj_a: str, obj_b: str) -> float:
        """
        Compares two NURBS surfaces and returns:
        - percentage difference (based on radius)
        - estimated angle (based on cosine relationship)

        Args:
            obj_a (str): reference object (true size)
            obj_b (str): compared object (projected/tilted)

        Returns:
            (percent, angle_degrees)
        """

        r1: float = self.get_nurbs_surface_radius(obj_a)
        r2: float = self.get_nurbs_surface_radius(obj_b)

        if r1 == 0:
            raise RuntimeError(f"{obj_a} has zero radius")

        ratio: float = r2 / r1

        # Clamp for safety (floating point issues)
        ratio = max(min(ratio, 1.0), -1.0)

        angle_rad: float = math.acos(ratio)
        angle_deg: float = math.degrees(angle_rad)

        percent: float = ratio * 100.0

        return angle_deg

    def sphere_edge_loop_offsets(self, radius: float, num_loops: int) -> list:
        """
        Returns Y offsets from center loop (equator) to pole on a sphere.
        """
        offsets = []

        for i in range(num_loops + 1):
            t = i / float(num_loops)  # 0 → 1
            theta = t * (math.pi / 2)  # equator → pole
            y = radius * math.sin(theta)
            offsets.append(y)

        return offsets

    def create_eye_preview_circle(self, name_suffix: str, parent: str) -> str:
        eye_radius: float = self.get_nurbs_surface_radius(self.guides["eye_diam"])

        eye_center_pos = get_position(self.guides["center_piv"])

        crv = cmds.circle(  # type:ignore
            name=f"center_preview_{name_suffix}_crv",
            radius=eye_radius,
            center=eye_center_pos,  # type:ignore
            normal=[0, 0, 1],  # type:ignore
            sections=16,
            degree=3,
        )[0]

        cmds.parent(crv, parent)  # type:ignore

        return crv  # type:ignore

    def build_eyeball(self) -> None:
        eye_radius: float = self.get_nurbs_surface_radius(self.guides[f"eye_diam"])

        pupil_degree: float = round(
            self.compare_radius_and_angle(self.guides[f"eye_diam"], self.guides[f"pupil_diam"])
        )

        iris_degree: float = round(
            self.compare_radius_and_angle(self.guides[f"eye_diam"], self.guides[f"iris_diam"])
        )

        pupil_percent = pupil_degree / 90
        iris_percent = iris_degree / 90

        eye_center_pos = get_position(self.guides[f"center_piv"])

        percents = [0, iris_percent, iris_degree]

        cmds.addAttr(
            self.main_ctrl,
            longName="pupil_dilation",
            attributeType="double",
            minValue=0 - (pupil_percent * 10),
            maxValue=10 - (pupil_percent * 10),
        )
        cmds.addAttr(
            self.main_ctrl,
            longName="iris_dilation",
            attributeType="double",
            minValue=0 - (iris_percent * 10),
            maxValue=10 - (iris_percent * 10),
        )
        dilation_offset = create_transform(
            name=f"dilation_{self.side}_Offset",
            parent=self.main_ctrl,
            transform=self.guides["center_piv"],
        )

        self.preview_circles = []
        for i, type in enumerate(iterable=["center", "iris", "pupil"]):
            circle = self.create_eye_preview_circle(
                name_suffix=f"{type}_{self.side}", parent=f"{dilation_offset}"
            )
            self.preview_circles.append(circle)
            if type == "center":
                pass
            else:
                dilation_mult = MultiplyDivideNode(name=f"{type}_dilation_mult_{self.side}_MD")
                dilation_offset = AddDLNode(name=f"{type}_dilation_mult_{self.side}_MD")
                cmds.setAttr(f"{dilation_mult.input2.x}", 18)  # type:ignore
                cmds.setAttr(f"{dilation_offset.input_1}", percents[i] * 10)  # type:ignore
                cmds.connectAttr(f"{self.main_ctrl}.{type}_dilation", f"{dilation_offset.input_2}")
                cmds.connectAttr(f"{dilation_offset.output}", f"{dilation_mult.input1.x}")

        # joints
        loops_list = self.sphere_edge_loop_offsets(radius=eye_radius, num_loops=10)

        dilation_joints = []

        for i, loop in enumerate(loops_list):
            if i == 0:
                parent = self.joint_parent
            else:
                parent = dilation_joints[0]

            jnt = create_joint(
                name=f"eye_dilation_{i:02d}_{self.side}",
                parent=parent,
                transform=self.guides[f"center_piv"],
                connect=False,
            )
            dilation_joints.append(jnt)
            cmds.setAttr(f"{jnt}.translateZ", loops_list[i])

            x = i / 10.0
            if x < iris_percent:
                blend = ["center", "iris"]
                blend_num = x / iris_percent

            elif x < pupil_percent:
                blend = ["iris", "pupil"]
                blend_num = (x - iris_percent) / (pupil_percent - iris_percent)

            else:
                blend = ["pupil", "center"]
                blend_num = (x - pupil_percent) / (1.0 - pupil_percent)

            print(f"{blend} {blend_num}")

            """if i / 10 < iris_percent:
                blend: list[str] = ["center", "iris"]
                blend_num: float = (i / 10) / iris_percent
            elif i / 10 == iris_percent:
                blend: list[str] = ["iris", "iris"]
                blend_num: float = 1.0
            elif iris_percent < i / 10 < pupil_percent:
                blend: list[str] = ["iris", "pupil"]
                blend_num: float = ( i / 10 - pupil_percent) / (iris_percent - pupil_percent)
            elif i / 10 > pupil_percent:
                blend: list[str] = ["pupil", "center"]
                blend_num: float = (i / 10) / pupil_percent
            else:
                blend: list[str] = ["center", "center"]
                blend_num: float = 1.0"""
