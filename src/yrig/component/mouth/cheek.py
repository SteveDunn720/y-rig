from dataclasses import dataclass
from typing import Sequence

from yrig.component.mouth.lip import Lip
from yrig.control import Control
from yrig.maya_api.attribute import BooleanAttribute
from yrig.spline import generate_knots
from yrig.spline.curve import bound_curve_from_transforms
from yrig.surface import uv_pin_multi
from yrig.transform import create_transform


@dataclass
class CheekInterpolateGuides:
    max_upper_mid_cv: str = "mouth_interpolate_max_M_upper_jnt"
    max_lower_mid_cv: str = "mouth_interpolate_max_M_lower_jnt"
    max_left_corner: str = "mouth_interpolate_max_L_corner_jnt"
    max_right_corner: str = "mouth_interpolate_max_R_corner_jnt"
    max_upper_left_cvs: Sequence[str] = (
        "mouth_interpolate_max_L_upper_cv0_jnt",
        "mouth_interpolate_max_L_upper_cv1_jnt",
    )
    max_upper_right_cvs: Sequence[str] = (
        "mouth_interpolate_max_R_upper_cv0_jnt",
        "mouth_interpolate_max_R_upper_cv1_jnt",
    )
    max_lower_left_cvs: Sequence[str] = (
        "mouth_interpolate_max_L_lower_cv0_jnt",
        "mouth_interpolate_max_L_lower_cv1_jnt",
    )
    max_lower_right_cvs: Sequence[str] = (
        "mouth_interpolate_max_R_lower_cv0_jnt",
        "mouth_interpolate_max_R_lower_cv1_jnt",
    )


class CheekInterpolateSpline:
    def __init__(self, name: str, cvs: Sequence[str], parent: str):
        self.curve = bound_curve_from_transforms(
            cvs, f"{name}_curve", knots=generate_knots(len(cvs), clamped=False), parent=parent
        )


def _create_cv_transforms(name_format: str, cv_guides: Sequence[str], parent: str) -> list[str]:
    transforms: list[str] = []
    for index, cv_guide in enumerate(cv_guides):
        transform = create_transform(f"{name_format}{index}", transform=cv_guide, parent=parent)
        transforms.append(transform)
    return transforms


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
        self.name = "cheek_interpolate"
        self.group = create_transform(f"{self.name}_grp", parent=parent)

        cheek_max_name = "cheek_max_interp"

        self.max_upper_mid_cv = create_transform(
            f"{cheek_max_name}_upper_M", transform=self.guides.max_upper_mid_cv, parent=self.group
        )
        self.max_lower_mid_cv = create_transform(
            f"{cheek_max_name}_lower_M", transform=self.guides.max_lower_mid_cv, parent=self.group
        )
        self.max_left_corner_cv = create_transform(
            f"{cheek_max_name}_corner_L", transform=self.guides.max_left_corner, parent=self.group
        )
        self.max_right_corner_cv = create_transform(
            f"{cheek_max_name}_corner_R", transform=self.guides.max_right_corner, parent=self.group
        )
        self.max_upper_left_cvs = _create_cv_transforms(
            f"{cheek_max_name}_upper_L_cv",
            cv_guides=self.guides.max_upper_left_cvs,
            parent=self.group,
        )
        self.max_upper_right_cvs = _create_cv_transforms(
            f"{cheek_max_name}_upper_R_cv",
            cv_guides=self.guides.max_upper_right_cvs,
            parent=self.group,
        )
        self.max_lower_left_cvs = _create_cv_transforms(
            f"{cheek_max_name}_lower_L_cv",
            cv_guides=self.guides.max_lower_left_cvs,
            parent=self.group,
        )
        self.max_lower_right_cvs = _create_cv_transforms(
            f"{cheek_max_name}_lower_R_cv",
            cv_guides=self.guides.max_lower_right_cvs,
            parent=self.group,
        )
        self.cv_transforms = (
            [self.max_upper_mid_cv]
            + [self.max_lower_mid_cv]
            + [self.max_left_corner_cv]
            + [self.max_right_corner_cv]
            + self.max_upper_left_cvs
            + self.max_upper_right_cvs
            + self.max_lower_left_cvs
            + self.max_lower_right_cvs
        )

        self.max_upper_left_full_cvs = (
            [self.max_upper_right_cvs[0]]
            + [self.max_upper_mid_cv]
            + self.max_upper_left_cvs
            + [self.max_left_corner_cv]
            + [self.max_lower_left_cvs[-1]]
        )
        self.max_upper_right_full_cvs = (
            [self.max_upper_left_cvs[0]]
            + [self.max_upper_mid_cv]
            + self.max_upper_right_cvs
            + [self.max_right_corner_cv]
            + [self.max_lower_right_cvs[-1]]
        )

        self.max_lower_left_full_cvs = (
            [self.max_lower_right_cvs[0]]
            + [self.max_lower_mid_cv]
            + self.max_lower_left_cvs
            + [self.max_left_corner_cv]
            + [self.max_upper_left_cvs[-1]]
        )
        self.max_lower_right_full_cvs = (
            [self.max_lower_left_cvs[0]]
            + [self.max_lower_mid_cv]
            + self.max_lower_right_cvs
            + [self.max_right_corner_cv]
            + [self.max_upper_right_cvs[-1]]
        )

        self.upper_left_max_spline = CheekInterpolateSpline(
            name=f"{cheek_max_name}_upper_L", cvs=self.max_upper_left_full_cvs, parent=self.group
        )
        self.upper_right_max_spline = CheekInterpolateSpline(
            name=f"{cheek_max_name}_upper_R", cvs=self.max_upper_right_full_cvs, parent=self.group
        )
        self.lower_left_max_spline = CheekInterpolateSpline(
            name=f"{cheek_max_name}_lower_L", cvs=self.max_lower_left_full_cvs, parent=self.group
        )
        self.lower_right_max_spline = CheekInterpolateSpline(
            name=f"{cheek_max_name}_lower_R", cvs=self.max_lower_right_full_cvs, parent=self.group
        )

        cheek_max_name = "cheek_max_interpolate"
        self.uv_pin = uv_pin_multi(f"{cheek_max_name}_uvPin", mouth_surface, self.cv_transforms)
