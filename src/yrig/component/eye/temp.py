from yrig.control import create_control
from yrig.joint import create_joint

guide = "face_top_M"
name = "hat"
side = "M"
control_parent = ""
joint_parent = ""
control_size = 1
build: bool = False

if build:
    ctrl = create_control(
        name=f"{name}_{side}",
        parent=control_parent,
        transform=guide,
        size=control_size,
        control_shape="circle",
    )

    jnt = create_joint(
        name=f"{name}_{side}",
        parent=joint_parent,
        transform=ctrl.transform,
    )
