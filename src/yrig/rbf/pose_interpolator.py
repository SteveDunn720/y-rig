from pathlib import Path

import maya.cmds as cmds
import maya.mel as mel


def import_pose_interpolator(path: Path, pose_interp_parent: str) -> None:
    try:
        existing_pose_interps = set(cmds.ls(type="poseInterpolator"))

        mel.eval(f'poseInterpolatorImportPoses "{path}" 1;')

        created_pose_interps = list(set(cmds.ls(type="poseInterpolator")) - existing_pose_interps)

        if pose_interp_parent and created_pose_interps:
            cmds.parent(created_pose_interps, pose_interp_parent)  # type:ignore

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


# taking it out of mel and into python kinda works, however the python wrapper doesnt handel the connected blendshapes at all, so i would have to write some tooling for handeling the blendshapes on my own, which i dont have the time to do, if i have time ill com back to it, but until then im going to stick with mel.
"""from pathlib import Path

import maya.cmds as cmds


def import_pose_interpolator(path: Path, pose_interp_parent: str) -> None:
    try:
        before = set(cmds.ls(type="poseInterpolator"))

        created = cmds.poseInterpolator(importPoses=str(path))

        # Some Maya commands return None, some return a string/list.
        # Fall back to finding newly-created nodes if needed.
        if not created:
            after = set(cmds.ls(type="poseInterpolator"))
            created = list(after - before)

        if isinstance(created, str):
            created = [created]

        if created and pose_interp_parent:
            cmds.parent(created, pose_interp_parent)  # type:ignore

    except Exception as e:
        cmds.warning(str(e))


def export_pose_interpolator(path: Path, pose_interp: str) -> None:
    try:
        cmds.poseInterpolator(
            pose_interp,
            edit=True,
            exportPoses=str(path),
        )

    except Exception as e:
        cmds.warning(str(e))



"""
