from dataclasses import dataclass

from maya import cmds

from yrig.control import Control, ControlShape, create_control
from yrig.joint import create_joint
from yrig.maya_api.enum import RotateOrder
from yrig.spline.curve import bound_curve_from_transforms
from yrig.spline.matrix_spline.build import JointConfig, matrix_spline_from_transforms
from yrig.surface import surface_slide_constraint
from yrig.transform import create_transform, matrix_constraint
from yrig.transform.matrix import local_constraint, localize_world_matrix

from .corner import BeanMouthCorner
from .lip import BeanMouthLip, BeanMouthLipGuides


@dataclass
class BeanMouthGuides:
    mouth: str
    jaw: str
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

        reference_space = str(control_parent)

        self.mouth_control = create_control(
            "mouth_M",
            transform=guides.mouth,
            parent=control_parent,
            size=control_size * 5,
            control_shape=ControlShape.LINE,
            direction="z",
        )
        self.jaw_control = create_control(
            "jaw_M",
            transform=guides.jaw,
            parent=control_parent,
            size=control_size * 8,
            control_shape=ControlShape.LINE,
            direction="z",
            rotation_order=RotateOrder.YZX,
        )
        self.jaw_joint = create_joint(name="jaw_M", transform=self.jaw_control, parent=joint_parent)
        self.jaw_blend = create_transform(
            "jaw_M_blend", parent=parent, transform=self.jaw_control.transform
        )
        self.mouth_slide = create_transform(f"mouth_M_slide", parent=self.mouth_control.transform)
        surface_slide_constraint(
            self.mouth_surface,
            driver_transform=self.mouth_control.transform,
            slider_transform=self.mouth_slide,
        )
        cmds.parentConstraint(
            self.jaw_control.transform,
            reference_space,
            self.jaw_blend,
            maintainOffset=True,
        )
        self.jaw_blend_local = create_transform(
            "jaw_M_blend_local", parent=self.mouth_slide, transform=self.jaw_control.transform
        )
        local_constraint(self.jaw_blend, self.jaw_blend_local, reference_space=reference_space)

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

        matrix_constraint(self.jaw_blend_local, self.left_corner.main_control.offset)
        matrix_constraint(self.jaw_blend_local, self.right_corner.main_control.offset)

        self.upper_lip = BeanMouthLip(
            upper=True,
            guides=guides.upper_lip,
            mouth_surface=self.mouth_surface,
            left_corner=self.left_corner,
            right_corner=self.right_corner,
            parent=parent,
            joint_parent=joint_parent,
            control_parent=self.mouth_slide,
            control_size=control_size,
        )
        self.lower_lip = BeanMouthLip(
            upper=False,
            guides=guides.lower_lip,
            mouth_surface=self.mouth_surface,
            left_corner=self.left_corner,
            right_corner=self.right_corner,
            parent=parent,
            joint_parent=joint_parent,
            control_parent=self.mouth_slide,
            control_size=control_size,
        )

        local_constraint(
            self.jaw_control.transform, self.lower_lip.lip_move, reference_space=reference_space
        )
