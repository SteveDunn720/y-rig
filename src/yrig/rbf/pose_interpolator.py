from pathlib import Path

import maya.cmds as cmds
import maya.mel as mel


def import_pose_interpolator(path: Path, pose_interp_parent: str) -> None:
    try:
        mel.eval(f'poseInterpolatorImportPoses "{path}" 1;')
        cmds.select("*_poseInterpolator")
        pose_interp = cmds.ls(selection=True)
        if pose_interp_parent:
            cmds.parent(pose_interp, pose_interp_parent)  # type:ignore
    except Exception as e:
        cmds.warning(str(e))


def export_pose_interpolator(path: Path, pose_interp: str) -> None:
    try:
        pose_path: str = str(path)

        mel.eval(
            f'''
            string $tpls[] = {{"{pose_interp}"}};
            string $poses[] = {{}};
            poseInterpolatorExportPoses("{pose_path}", $tpls, $poses, 1);
            '''
        )

    except Exception as e:
        cmds.warning(str(e))
