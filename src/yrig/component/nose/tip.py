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

    def build_tip(self) -> None:

        # Bridge

        self.bridge_ctrl = create_control(
            name=self.guides["bridge"],
            parent=self.main_ctrl,
            transform=self.guides["bridge"],
            size=self.control_size * 0.5,
            control_shape="circle",
            direction="z",
        )

        self.bridge_jnt = create_joint(
            name=self.guides["bridge"],
            transform=self.bridge_ctrl,
            parent=self.joint_parent,
        )

        # Tip

        self.tip_ctrl = create_control(
            name=self.guides["tip"],
            parent=self.bridge_ctrl.transform,
            transform=self.guides["tip"],
            size=self.control_size * 0.45,
            control_shape="circle",
            direction="z",
        )

        self.tip_jnt = create_joint(
            name=self.guides["tip"],
            transform=self.tip_ctrl,
            parent=self.bridge_jnt,
        )

        # Left Nostril

        self.left_ctrl = create_control(
            name=self.guides["nose_L"],
            parent=self.tip_ctrl.transform,
            transform=self.guides["nose_L"],
            size=self.control_size * 0.35,
            control_shape="circle",
            direction="z",
        )

        self.left_jnt = create_joint(
            name=self.guides["nose_L"],
            transform=self.left_ctrl,
            parent=self.tip_jnt,
        )

        # Right Nostril

        self.right_ctrl = create_control(
            name=self.guides["nose_R"],
            parent=self.tip_ctrl.transform,
            transform=self.guides["nose_R"],
            size=self.control_size * 0.35,
            control_shape="circle",
            direction="z",
        )

        self.right_jnt = create_joint(
            name=self.guides["nose_R"],
            transform=self.right_ctrl,
            parent=self.tip_jnt,
        )
