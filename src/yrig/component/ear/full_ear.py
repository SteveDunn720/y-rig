from yrig.control import create_control
from yrig.joint import create_joint


class FullEar:
    def __init__(
        self,
        side: str,
        guides: dict,
        main_ctrl: str,
        joint_parent: str,
        control_grp: str,
        component_grp: str,
        control_size: float = 1.0,
    ):
        self.side = side
        self.guides = guides
        self.main_ctrl = main_ctrl
        self.joint_parent = joint_parent
        self.control_grp = control_grp
        self.component_grp = component_grp
        self.control_size = control_size

    def build_tip(self) -> None:
        self.center_ctrl = create_control(
            name=f"ear_main_{self.side}",
            parent=self.main_ctrl,
            transform=self.guides[f"ear_{self.side}"],
            size=self.control_size * 0.35,
            control_shape="circle",
            direction="z",
        )

        self.center_jnt = create_joint(
            name=f"ear_main_{self.side}",
            transform=self.center_ctrl,
            parent=self.joint_parent,
        )