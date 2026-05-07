from dataclasses import dataclass, field
from os import name
from typing import Literal

from maya import cmds

from yrig import surface
from yrig.control import ControlShape, create_control
from yrig.control.core import Control
from yrig.maya_api.attribute import BooleanAttribute, ScalarAttribute
from yrig.maya_api.node import MultiplyNode, SubtractNode
from yrig.spline.curve import bound_curve_from_transforms
from yrig.spline.matrix_spline.build import JointConfig, matrix_spline_from_transforms
from yrig.surface import surface_slide_constraint
from yrig.transform import create_transform


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
        mouth_surface: str,
        parent: str,
        control_parent: Control | str,
        control_size: float = 1,
        sub_control_vis_attr: BooleanAttribute | None = None,
    ):
        self.guides = guides
        self.lip_move = create_transform(f"{side}_lip_move", parent=str(control_parent))
        self.slider = create_transform(f"{side}_lip_slide", parent=str(control_parent))
        surface_slide_constraint(
            mouth_surface, driver_transform=self.lip_move, slider_transform=self.slider
        )

        self.mid_left_control = create_control(
            f"{side}_lip_mid_L",
            transform=guides.lip_mid_left,
            parent=self.slider,
            size=control_size,
            direction="z",
        )
        self.mid_control = create_control(
            f"{side}_lip_mid_M",
            transform=guides.lip_mid,
            parent=self.slider,
            size=control_size,
            direction="z",
        )
        self.mid_right_control = create_control(
            f"{side}_lip_mid_R",
            transform=guides.lip_mid_right,
            parent=self.slider,
            size=control_size,
            direction="z",
        )

        for control in (self.mid_left_control, self.mid_control, self.mid_right_control):
            cmds.setAttr(f"{control.transform}.translateZ", lock=True)

        self.mid_left_sub_control = create_control(
            f"{side}_lip_mid_L_sub",
            transform=guides.lip_mid_left,
            parent=self.mid_left_control,
            size=control_size * 0.5,
            direction="z",
        )
        surface_slide_constraint(
            mouth_surface,
            driver_transform=self.mid_left_control.transform,
            slider_transform=self.mid_left_sub_control.offset,
        )
        self.mid_sub_control = create_control(
            f"{side}_lip_mid_M_sub",
            transform=guides.lip_mid,
            parent=self.mid_control,
            size=control_size * 0.5,
            direction="z",
        )
        surface_slide_constraint(
            mouth_surface,
            driver_transform=self.mid_control.transform,
            slider_transform=self.mid_sub_control.offset,
        )
        self.mid_right_sub_control = create_control(
            f"{side}_lip_mid_R_sub",
            transform=guides.lip_mid_right,
            parent=self.mid_right_control,
            size=control_size * 0.5,
            direction="z",
        )
        surface_slide_constraint(
            mouth_surface,
            driver_transform=self.mid_right_control.transform,
            slider_transform=self.mid_right_sub_control.offset,
        )

        self.sub_controls: list[Control] = [
            self.mid_left_sub_control,
            self.mid_sub_control,
            self.mid_right_control,
        ]

        if sub_control_vis_attr is not None:
            for control in self.sub_controls:
                sub_control_vis_attr.connect_to(f"{control.transform}.visibility")


class BeanMouthCorner:
    def __init__(
        self,
        side: Literal["L"] | Literal["R"],
        guide: str,
        mouth_surface: str,
        control_parent: Control | str,
        control_size: float = 1,
        sub_control_vis_attr: BooleanAttribute | None = None,
    ):
        self.main_control = create_control(
            f"mouth_corner_{side}",
            transform=guide,
            parent=control_parent,
            size=control_size,
            direction="z",
        )
        self.sub_control = create_control(
            f"mouth_corner_{side}_sub",
            transform=guide,
            parent=self.main_control,
            size=control_size * 0.5,
            direction="z",
        )

        surface_slide_constraint(
            mouth_surface,
            driver_transform=self.main_control.transform,
            slider_transform=self.sub_control.offset,
        )

        self.upper_control = create_control(
            f"mouth_corner_{side}_up",
            transform=self.sub_control.offset,
            parent=self.sub_control.offset,
            size=control_size * 0.5,
            direction="z",
        )
        self.lower_control = create_control(
            f"mouth_corner_{side}_lo",
            transform=self.sub_control.offset,
            parent=self.sub_control.offset,
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

        upper_roundness_scaled.output.connect_to(f"{self.upper_control.offset}.translateY")
        lower_roundness_scaled.output.connect_to(f"{self.lower_control.offset}.translateY")
        roundness_side_offset.output.connect_to(f"{self.upper_control.offset}.translateX")
        roundness_side_offset.output.connect_to(f"{self.lower_control.offset}.translateX")

        self.upper_sub_control = create_control(
            f"mouth_corner_{side}_up_sub",
            transform=self.upper_control.transform,
            parent=self.upper_control,
            size=control_size * 0.5,
            direction="z",
        )
        surface_slide_constraint(
            mouth_surface, self.upper_control.transform, self.upper_sub_control.offset
        )
        self.lower_sub_control = create_control(
            f"mouth_corner_{side}_lo_sub",
            transform=self.upper_control.transform,
            parent=self.lower_control,
            size=control_size * 0.5,
            direction="z",
        )
        surface_slide_constraint(
            mouth_surface, self.lower_control.transform, self.lower_sub_control.offset
        )

        self.sub_controls: list[Control] = [
            self.sub_control,
            self.upper_sub_control,
            self.lower_sub_control,
        ]

        if sub_control_vis_attr is not None:
            for control in self.sub_controls:
                sub_control_vis_attr.connect_to(f"{control.transform}.visibility")


class BeanMouth:
    def __init__(
        self,
        guides: BeanMouthGuides,
        mouth_surface: str,
        parent: str,
        control_parent: Control | str,
        joint_parent: str,
        control_size: float = 1,
    ):
        self.guides = guides

        duplicated_mouth_surface = cmds.duplicate(mouth_surface)[0]
        cmds.parent(duplicated_mouth_surface, parent)
        self.mouth_surface = cmds.rename(duplicated_mouth_surface, "mouth_surface")
        cmds.hide(self.mouth_surface)

        self.mouth_control = create_control(
            "mouth_M",
            transform=guides.mouth,
            parent=control_parent,
            size=control_size * 5,
            control_shape=ControlShape.LINE,
            direction="z",
        )
        self.mouth_slide = create_transform(f"mouth_M_slide", parent=self.mouth_control.transform)
        surface_slide_constraint(
            self.mouth_surface,
            driver_transform=self.mouth_control.transform,
            slider_transform=self.mouth_slide,
        )

        self.left_corner = BeanMouthCorner(
            side="L",
            guide=guides.left_corner,
            mouth_surface=self.mouth_surface,
            control_parent=self.mouth_slide,
            control_size=control_size,
        )
        self.right_corner = BeanMouthCorner(
            side="R",
            guide=guides.right_corner,
            mouth_surface=self.mouth_surface,
            control_parent=self.mouth_slide,
            control_size=control_size,
        )

        self.upper_lip = BeanMouthLip(
            "upper",
            guides=guides.upper_lip,
            mouth_surface=self.mouth_surface,
            parent=parent,
            control_parent=self.mouth_slide,
            control_size=control_size,
        )
        self.lower_lip = BeanMouthLip(
            "lower",
            guides=guides.lower_lip,
            mouth_surface=self.mouth_surface,
            parent=parent,
            control_parent=self.mouth_slide,
            control_size=control_size,
        )

        mouth_cv_controls: tuple[Control, ...] = (
            self.left_corner.sub_control,
            self.left_corner.upper_sub_control,
            self.upper_lip.mid_left_sub_control,
            self.upper_lip.mid_sub_control,
            self.upper_lip.mid_right_sub_control,
            self.right_corner.upper_sub_control,
            self.right_corner.sub_control,
            self.right_corner.lower_sub_control,
            self.lower_lip.mid_right_sub_control,
            self.lower_lip.mid_sub_control,
            self.lower_lip.mid_left_sub_control,
            self.left_corner.lower_sub_control,
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
