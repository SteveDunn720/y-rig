from dataclasses import dataclass

from yrig.control import Control, ControlShape, create_control
from yrig.joint import create_joint
from yrig.maya_api.enum import RotateOrder
from yrig.transform import create_transform, matrix_constraint
from yrig.transform.matrix import local_constraint


@dataclass
class FaceBaseGuides:
    lower: str = "face_lower_M"
    muppet: str = "face_muppet_M"
    upper: str = "face_upper_M"
    top: str = "face_top_M"
    jaw: str = "jaw_M"


class FaceBase:
    def __init__(
        self,
        guides: FaceBaseGuides,
        parent: str,
        control_parent: Control | str,
        joint_parent: str,
        control_size: float = 5,
    ):
        self.guides = guides
        reference_space = str(control_parent)

        self.lower_control = create_control(
            "face_lower_M",
            transform=guides.lower,
            parent=control_parent,
            size=control_size,
            control_shape=ControlShape.SQUARE,
            direction="y",
        )
        self.lower_joint = create_joint(
            name="face_lower_M", transform=self.lower_control, parent=joint_parent
        )

        self.jaw_control = create_control(
            "jaw_M",
            transform=guides.jaw,
            parent=self.lower_control,
            size=control_size * 8,
            control_shape=ControlShape.LINE,
            direction="z",
            rotation_order=RotateOrder.YZX,
        )
        self.jaw_joint = create_joint(
            name="jaw_M", transform=self.jaw_control, parent=self.lower_joint
        )

        self.muppet_control = create_control(
            "face_muppet_M",
            transform=guides.muppet,
            parent=control_parent,
            size=control_size,
            control_shape=ControlShape.CIRCLE,
            direction="y",
        )
        self.muppet_joint = create_joint(
            name="face_muppet_M", transform=self.muppet_control, parent=joint_parent
        )
        self.muppet_space = create_transform(
            "face_muppet_M_space", transform=self.muppet_control.transform, parent=parent
        )
        matrix_constraint(self.muppet_control.transform, self.muppet_space)
        self.mid_driven = create_transform("face_mid_M_driven", parent=self.muppet_space)

        local_constraint(self.lower_control.transform, self.mid_driven, reference_space)
        self.mid_joint = create_joint(
            name="face_mid_M",
            transform=self.muppet_control,
            parent=self.muppet_joint,
            connect=False,
        )
        matrix_constraint(self.mid_driven, self.mid_joint)

        self.upper_control = create_control(
            "face_upper_M",
            transform=guides.upper,
            parent=self.muppet_control,
            size=control_size,
            control_shape=ControlShape.SQUARE,
            direction="y",
        )
        self.upper_joint = create_joint(
            "face_upper_M", transform=self.upper_control, parent=self.mid_joint
        )

        self.top_control = create_control(
            "face_top_M",
            transform=guides.top,
            parent=self.upper_control,
            size=control_size,
            control_shape=ControlShape.SQUARE,
            direction="y",
        )
        self.top_joint = create_joint(
            "face_top_M", transform=self.top_control, parent=self.upper_joint
        )
