from dataclasses import dataclass

from yrig.control import ControlShape, create_control
from yrig.control.core import Control


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
        self.lip_mid_left_control = create_control(
            f"{side}_lip_mid_L",
            transform=guides.lip_mid_left,
            parent=control_parent,
            size=control_size,
            direction="z",
        )
        self.lip_mid_control = create_control(
            f"{side}_lip_mid_M",
            transform=guides.lip_mid,
            parent=control_parent,
            size=control_size,
            direction="z",
        )
        self.lip_mid_right_control = create_control(
            f"{side}_lip_mid_R",
            transform=guides.lip_mid_right,
            parent=control_parent,
            size=control_size,
            direction="z",
        )


class BeanMouth:
    def __init__(
        self, guides: BeanMouthGuides, control_parent: Control | str, control_size: float = 1
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
        self.left_corner_control = create_control(
            "mouth_corner_L",
            transform=guides.left_corner,
            parent=self.mouth_control,
            size=control_size,
            control_shape=ControlShape.TRIANGLE,
            direction="z",
        )
        self.right_corner_control = create_control(
            "mouth_corner_R",
            transform=guides.right_corner,
            parent=self.mouth_control,
            size=control_size,
            control_shape=ControlShape.TRIANGLE,
            direction="z",
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
