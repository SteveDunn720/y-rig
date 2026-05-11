from dataclasses import dataclass

from maya import cmds

from yrig.control import Control, create_control
from yrig.joint import collect_joints, create_joint
from yrig.maya_api.attribute import BooleanAttribute
from yrig.skin.split import tag_for_weight_split
from yrig.spline.curve import bound_curve_from_transforms, pin_to_curve_with_motion_path
from yrig.surface import surface_slide_constraint
from yrig.transform import create_transform

from .corner import BeanMouthCorner


@dataclass
class BeanMouthLipGuides:
    lip_mid_left: str
    lip_mid: str
    lip_mid_right: str


class BeanMouthLip:
    def __init__(
        self,
        upper: bool,
        guides: BeanMouthLipGuides,
        mouth_surface: str,
        left_corner: BeanMouthCorner,
        right_corner: BeanMouthCorner,
        parent: str,
        joint_parent: str,
        control_parent: Control | str,
        control_size: float = 1,
        sub_control_vis_attr: BooleanAttribute | None = None,
    ):
        self.guides = guides
        side_string = "upper" if upper else "lower"
        self.name = f"{side_string}_lip"
        self.lip_move = create_transform(f"{self.name}_move", parent=str(control_parent))
        self.slider = create_transform(f"{self.name}_slide", parent=str(control_parent))
        surface_slide_constraint(
            mouth_surface, driver_transform=self.lip_move, slider_transform=self.slider
        )

        self.left_corner = left_corner
        self.right_corner = right_corner

        self.mid_left_control = create_control(
            f"{self.name}_mid_L",
            transform=guides.lip_mid_left,
            parent=self.slider,
            size=control_size,
            direction="z",
        )
        self.mid_control = create_control(
            f"{self.name}_mid_M",
            transform=guides.lip_mid,
            parent=self.slider,
            size=control_size,
            direction="z",
        )
        self.mid_right_control = create_control(
            f"{self.name}_mid_R",
            transform=guides.lip_mid_right,
            parent=self.slider,
            size=control_size,
            direction="z",
        )

        for control in (self.mid_left_control, self.mid_control, self.mid_right_control):
            cmds.setAttr(f"{control.transform}.translateZ", lock=True)

        self.mid_left_sub_control = create_control(
            f"{self.name}_mid_L_sub",
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
            f"{self.name}_mid_M_sub",
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
            f"{self.name}_mid_R_sub",
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

        lip_cvs: tuple[Control, ...] = (
            self.mid_left_sub_control,
            self.mid_sub_control,
            self.mid_right_sub_control,
        )

        left_corner_cvs: tuple[Control, ...] = (
            self.left_corner.lower_sub_control,
            self.left_corner.sub_control,
            self.left_corner.upper_sub_control,
        )
        right_corner_cvs: tuple[Control, ...] = (
            self.right_corner.upper_sub_control,
            self.right_corner.sub_control,
            self.right_corner.lower_sub_control,
        )

        if upper:
            full_lip_cvs = left_corner_cvs + lip_cvs + right_corner_cvs
        else:
            # Reverse order of corner controls for lower lip
            full_lip_cvs = left_corner_cvs[::-1] + lip_cvs + right_corner_cvs[::-1]

        degree = 3
        knots = [(i - degree) for i in range(len(full_lip_cvs) + degree + 1)]
        self.curve = bound_curve_from_transforms(
            [control.transform for control in full_lip_cvs],
            name=f"{self.name}_spline",
            parent=parent,
            degree=degree,
            knots=knots,
        )
        self.joint = create_joint(name=self.name, parent=joint_parent)
        segments = 24
        with collect_joints() as segment_joints:
            for i in range(segments):
                joint = create_joint(name=f"{self.curve}_seg{i}", parent=self.joint)
                pin_to_curve_with_motion_path(self.curve, joint, parameter=(i + 0.5) / segments)
        tag_for_weight_split(self.joint, segment_joints)
