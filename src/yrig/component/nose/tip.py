from yrig.control import create_control
from yrig.joint import create_joint


class NoseTip:
    def __init__(
        self,
        guides: dict,
        main_ctrl: str,
        joint_parent: str,
        control_grp: str,
        component_grp: str,
        control_size: float = 1.0,
    ):
        self.guides = guides
        self.main_ctrl = main_ctrl
        self.joint_parent = joint_parent
        self.control_grp = control_grp
        self.component_grp = component_grp
        self.control_size = control_size

    def build(self) -> None:

        self.tip_ctrl = create_control(
            name="nose_tip_M",
            parent=self.main_ctrl,
            transform=self.guides["tip"],
            size=self.control_size * 0.5,
            control_shape="circle",
            direction="z",
        )

        self.tip_jnt = create_joint(
            name="nose_tip_M",
            transform=self.tip_ctrl.transform,
            parent=self.joint_parent,
        )
