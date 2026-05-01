from dataclasses import dataclass, field
from typing import Literal

from yrig.control import ControlShape, create_control
from yrig.control.core import Control
from yrig.maya_api.attribute import ScalarAttribute
from yrig.maya_api.node import MultiplyNode, SubtractNode
from yrig.spline.curve import bound_curve_from_transforms
from yrig.spline.matrix_spline.build import JointConfig, matrix_spline_from_transforms


@dataclass
class BeanMouthLipGuides:
    left_corner: str
    right_corner: str
    lip_mid_left: str
    lip_mid: str
    lip_mid_right: str


@dataclass
class BeanMouthGuides:
    mouth: str
    left_corner: str
    right_corner: str
    upper_lip: BeanMouthLipGuides
    lower_lip: BeanMouthLipGuides


class BeanMouthLip:
    def __init__(
        self,
        side: str,
        guides: BeanMouthLipGuides,
        control_parent: Control | str,
        control_size: float = 1,
    ):
        self.guides = guides
        self.mid_left_control = create_control(
            f"{side}_lip_mid_L",
            transform=guides.lip_mid_left,
            parent=control_parent,
            size=control_size,
            direction="z",
        )
        self.mid_control = create_control(
            f"{side}_lip_mid_M",
            transform=guides.lip_mid,
            parent=control_parent,
            size=control_size,
            direction="z",
        )
        self.mid_right_control = create_control(
            f"{side}_lip_mid_R",
            transform=guides.lip_mid_right,
            parent=control_parent,
            size=control_size,
            direction="z",
        )


class BeanMouthCorner:
    def __init__(
        self,
        side: Literal["L"] | Literal["R"],
        guide: str,
        control_parent: Control | str,
        control_size: float = 1,
    ):
        self.main_control = create_control(
            f"mouth_corner_{side}",
            transform=guide,
            parent=control_parent,
            size=control_size,
            direction="z",
        )
        self.upper_control = create_control(
            f"mouth_corner_{side}_up",
            transform=guide,
            parent=self.main_control,
            size=control_size * 0.5,
            direction="z",
        )
        self.lower_control = create_control(
            f"mouth_corner_{side}_lo",
            transform=guide,
            parent=self.main_control,
            size=control_size * 0.5,
            direction="z",
        )
        self.roundness_attr = ScalarAttribute.create(
            self.main_control.transform,
            name="roundness",
            default=0,
            min=0,
        )
        upper_roundness_scaled = MultiplyNode(f"{self.main_control}_upper_roundness")
        upper_roundness_scaled.input[0].connect_from(self.roundness_attr)
        upper_roundness_scaled.input[1].set(0.5)
        lower_roundness_scaled = MultiplyNode(f"{self.main_control}_roundness_invert")
        lower_roundness_scaled.input[0].connect_from(self.roundness_attr)
        lower_roundness_scaled.input[1].set(-0.5)
        roundness_side_offset = MultiplyNode(f"{self.main_control}_roundness_side_offset")
        roundness_side_offset.input[0].connect_from(self.roundness_attr)
        roundness_side_offset.input[1].set(-0.25)

        upper_roundness_scaled.output.connect_to(f"{self.upper_control}.translateY")
        lower_roundness_scaled.output.connect_to(f"{self.lower_control}.translateY")
        roundness_side_offset.output.connect_to(f"{self.upper_control}.translateX")
        roundness_side_offset.output.connect_to(f"{self.lower_control}.translateX")


class BeanMouth:
    def __init__(
        self,
        guides: BeanMouthGuides,
        parent: str,
        control_parent: Control | str,
        joint_parent: str,
        control_size: float = 1,
    ):
        self.guides = guides
        self.mouth_control = create_control(
            "mouth_M",
            transform=guides.mouth,
            parent=control_parent,
            size=control_size * 5,
            control_shape=ControlShape.LINE,
            direction="z",
        )
        self.left_corner = BeanMouthCorner(
            side="L",
            guide=guides.left_corner,
            control_parent=self.mouth_control,
            control_size=control_size,
        )
        self.right_corner = BeanMouthCorner(
            side="R",
            guide=guides.right_corner,
            control_parent=self.mouth_control,
            control_size=control_size,
        )

        self.upper_lip = BeanMouthLip(
            "upper",
            guides=guides.upper_lip,
            control_parent=self.mouth_control,
            control_size=control_size,
        )
        self.lower_lip = BeanMouthLip(
            "lower",
            guides=guides.lower_lip,
            control_parent=self.mouth_control,
            control_size=control_size,
        )

        mouth_cv_controls: tuple[Control, ...] = (
            self.left_corner.main_control,
            self.left_corner.upper_control,
            self.upper_lip.mid_left_control,
            self.upper_lip.mid_control,
            self.upper_lip.mid_right_control,
            self.right_corner.upper_control,
            self.right_corner.main_control,
            self.right_corner.lower_control,
            self.lower_lip.mid_right_control,
            self.lower_lip.mid_control,
            self.lower_lip.mid_left_control,
            self.left_corner.lower_control,
        )

        joint_config = JointConfig(parent=joint_parent, weight_split_periodic=True)
        bound_curve_from_transforms(
            transforms=[control.transform for control in mouth_cv_controls],
            name="mouth_spline",
            parent=parent,
            periodic=True,
        )
        # self.mouth_spline = matrix_spline_from_transforms(
        #     "mouth_spline",
        #     cv_transforms=[control.transform for control in mouth_cv_controls],
        #     pinned_transforms=24,
        #     padded=True,
        #     joint_config=joint_config,
        #     stretch=False,
        #     interpolate_scale=False,
        #     parent=parent,
        #     periodic=True,
        #     primary_axis=(1, 0, 0),
        #     secondary_axis=(0, 0, 1),
        # )
