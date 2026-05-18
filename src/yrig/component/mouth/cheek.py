from dataclasses import dataclass

from yrig.component.mouth.lip import Lip
from yrig.control import Control
from yrig.maya_api.attribute import BooleanAttribute
from yrig.spline.curve import create_transforms_at_curve_cvs
from yrig.surface import uv_pin_multi


@dataclass
class CheekInterpolateGuides:
    max_curve: str


class CheekInterpolate:
    def __init__(
        self,
        guides: CheekInterpolateGuides,
        mouth_surface: str,
        upper_lip: Lip,
        lower_lip: Lip,
        parent: str,
        control_parent: Control | str,
        control_size: float = 1,
        sub_control_vis_attr: BooleanAttribute | None = None,
    ):
        self.guides = guides
        self.cv_transforms = create_transforms_at_curve_cvs(
            curve=self.guides.max_curve, parent=parent
        )
        uv_pin_multi("cheek_max_interpolate_uvPin", mouth_surface, self.cv_transforms)
