from dataclasses import dataclass

from maya import cmds

from yrig.control import Control, create_control
from yrig.maya_api.attribute import BooleanAttribute
from yrig.surface import surface_slide_constraint
from yrig.transform import create_transform


@dataclass
class BeanMouthLipGuides:
    left_corner: str
    right_corner: str
    lip_mid_left: str
    lip_mid: str
    lip_mid_right: str


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
