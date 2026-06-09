from yrig.control import create_control
from yrig.joint import create_joint


class Nostril:
    def __init__(
        self,
        side: str,
        guides: dict,
        main_ctrl: str,
        joint_parent: str,
        control_size: float = 1.0,
    ):
        self.side = side
        self.guides = guides
        self.main_ctrl = main_ctrl
        self.joint_parent = joint_parent
        self.control_size = control_size

    def build(self) -> None:

        guide = self.guides[f"nostril_{self.side}"]

        self.ctrl = create_control(
            name=f"nostril_{self.side}",
            parent=self.main_ctrl,
            transform=guide,
            size=self.control_size * 0.35,
            control_shape="circle",
            direction="z",
        )

        self.jnt = create_joint(
            name=f"nostril_{self.side}",
            transform=self.ctrl.transform,
            parent=self.joint_parent,
        )
