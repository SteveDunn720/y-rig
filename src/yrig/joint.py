from maya import cmds
from maya.api.OpenMaya import MMatrix

from yrig.build.mgear_api.joint import add_to_joint_set
from yrig.transform import match_transform, matrix_constraint, set_world_matrix

JOINT_SUFFIX: str = "_jnt"


def create_joint(name: str, transform: str | MMatrix, parent: str | None, connect: bool = True):
    joint = cmds.createNode("joint", name=f"{name}{JOINT_SUFFIX}")
    if parent is not None:
        cmds.parent(joint, parent, relative=True)
    if isinstance(transform, str):
        match_transform(joint, transform, use_joint_orient=True)
        if connect:
            matrix_constraint(transform, joint, False, use_joint_orient=True)

    elif isinstance(transform, MMatrix):
        set_world_matrix(joint, transform, use_joint_orient=True)
    else:
        raise RuntimeError(f"{transform} is not a valid transform name or MMatrix")
    add_to_joint_set(joint)
