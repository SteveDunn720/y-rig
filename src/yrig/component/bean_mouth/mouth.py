from dataclasses import dataclass

from maya import cmds

from yrig.control import Control, ControlShape, create_control
from yrig.spline.curve import bound_curve_from_transforms
from yrig.spline.matrix_spline.build import JointConfig
from yrig.surface import surface_slide_constraint
from yrig.transform import create_transform

from .corner import BeanMouthCorner
from .lip import BeanMouthLip, BeanMouthLipGuides


@dataclass
class BeanMouthGuides:
    mouth: str
    left_corner: str
    right_corner: str
    upper_lip: BeanMouthLipGuides
    lower_lip: BeanMouthLipGuides


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
        # cmds.sets(self.mouth_surface, add="rig_geo_grp")

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
