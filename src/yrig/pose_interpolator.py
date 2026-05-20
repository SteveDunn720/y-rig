import maya.cmds as cmds
from maya import mel


def import_poseInterpolator(path: str) -> None:
    try:
        mel.eval(f'poseInterpolatorImportPoses "{path}" 1;')
        cmds.select("*_poseInterpolator")
        pi = cmds.ls(selection=True)
        cmds.parent(pi, "RIG")  # type:ignore
    except Exception as e:
        cmds.warning(e)  # type:ignore
