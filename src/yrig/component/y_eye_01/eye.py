from typing import Any


from yrig.control import create_control
from yrig.joint import create_joint
from yrig.transform import create_transform
from yrig.component.y_eye_01.eyelid import Eyelid


class Eye:
    def __init__(
        self,
        part: str = "eye",
        side: str = "L",
        parent: str = "face_grp",
        control_parent: str = "neck_M0_head_ctl",
        control_size: float = 1.0,
    ):
        self.part: str = part
        self.side: str = side
        self.parent: str = parent
        self.control_parent: str = control_parent
        self.control_size: float = control_size

        self.guides: dict[str, str] = {
            "root_name": f"eye_root_{side}",
            "center_piv": f"eye_center_{self.side}",
            "aim": f"eye_aim_{self.side}",
            "eyelid_inner_corner": f"eyelid_innercorner_{self.side}",
            "eyelid_inner_upper": f"eyelid_innerupper_{self.side}",
            "eyelid_inner_lower": f"eyelid_innerlower_{self.side}",
            "eyelid_mid_upper": f"eyelid_upper_{self.side}",
            "eyelid_mid_lower": f"eyelid_lower_{self.side}",
            "eyelid_outer_upper": f"eyelid_outerupper_{self.side}",
            "eyelid_outer_lower": f"eyelid_outerlower_{self.side}",
            "eyelid_outer_corner": f"eyelid_outercorner_{self.side}",
            "eyelid_upper_curve": f"eyelid_upper_curve_{self.side}",
            "eyelid_lower_curve": f"eyelid_lower_curve_{self.side}",
        }

    # -------------------
    # Build steps
    # -------------------

    def setup_structure(self) -> None:
        self.main_grp = create_transform(name=f"eye_{self.side}", parent=self.parent)

    def create_controls(self) -> None:
        self.main_ctrl = create_control(
            name=self.guides["root_name"],
            parent=self.main_grp,
            transform=self.guides["center_piv"],
            size=self.control_size,
            control_shape="round_square",
            direction="z",
        )

    def create_joints(self) -> None:
        self.main_jnt = create_joint(
            name=self.guides["root_name"],
            parent=self.main_grp,
            transform=self.main_ctrl.transform,
        )

    def build(self) -> None:
        self.setup_structure()
        self.create_controls()
        self.create_joints()

        self.eyelid = Eyelid(
            side=self.side,
            guides=self.guides,
            control_size=self.control_size,
            main_ctrl=self.main_ctrl.transform,
            parent=self.main_grp,
            joint_parent=self.main_jnt,
        )

        self.eyelid.build_blink()
