import logging
from pathlib import Path

from maya import cmds

from yrig.deformer.blendshape import export_maya_shape_file, import_maya_shape_file
from yrig.rbf.pose_interpolator.core import (
    _reslove_pose_index,
    _validate_pose_interpolators,
    get_pose_interpolator_blendshapes,
    group_pose_interpolators_by_directory,
    resolve_pose_interpolator_shape,
)

log = logging.getLogger(__name__)


def import_maya_pose_file(
    filepath: Path, parent: str | None = None, import_shapes: bool = True
) -> set[str]:
    if filepath.suffix != ".pose":
        raise ValueError(f"The file at {filepath} is not a .pose file.")
    if not filepath.exists():
        raise FileNotFoundError(f"No .pose file found at {filepath}.")

    if import_shapes:
        for shp_file in filepath.parent.glob(f"{filepath.stem}.*.shp"):
            blendshape = shp_file.stem.removeprefix(f"{filepath.stem}.")
            import_maya_shape_file(shp_file, blendshape)

    existing_pose_interps = set(cmds.ls(type="poseInterpolator") or [])
    cmds.poseInterpolator(importPoses=str(filepath))
    current_pose_interps = set(cmds.ls(type="poseInterpolator") or [])
    created_pose_interps = current_pose_interps - existing_pose_interps
    group_pose_interpolators_by_directory(created_pose_interps, parent)
    log.info(f"Imported {len(created_pose_interps)} pose interpolator(s) from {filepath}")
    return created_pose_interps


def export_maya_pose_file(
    filepath: Path,
    pose_interpolators: list[str] | None = None,
    poses: list[tuple[str, str | int]] | None = None,
    export_shapes: bool = True,
) -> None:
    if pose_interpolators:
        resloved_pose_interpolators = [
            resolve_pose_interpolator_shape(pose_interpolator)
            for pose_interpolator in pose_interpolators
        ]
    elif poses:
        resloved_pose_interpolators = [
            resolve_pose_interpolator_shape(pose_interpolator) for pose_interpolator, _pose in poses
        ]
    else:
        raise ValueError("Must give pose_interpolators or poses for export")

    _validate_pose_interpolators(resloved_pose_interpolators)

    args = []
    if pose_interpolators:
        args.append(pose_interpolators)
    kwargs = {}
    if poses:
        kwargs["pose"] = poses

    cmds.poseInterpolator(
        *args,  # type: ignore
        **kwargs,  # type: ignore
        edit=True,
        exportPoses=str(filepath),
    )
    log.info(f"Exported pose interpolator(s) to {filepath}")

    if not export_shapes:
        return

    # Find connected shape deformers.
    blendshapes: list[str] = []

    for pose_interpolator in resloved_pose_interpolators:
        blendshapes.extend(get_pose_interpolator_blendshapes(pose_interpolator))

    for blendshape in blendshapes:
        shape_file = filepath.with_suffix(f".{blendshape}.shp")
        targets: list[str] = []
        destinations: list[str] = []
        if poses:
            for pose_interpolator, pose in poses:
                pose_index = _reslove_pose_index(pose_interpolator, pose)
                source = (
                    f"{resolve_pose_interpolator_shape(pose_interpolator)}.output[{pose_index}]"
                )
                destinations.extend(
                    cmds.connectionInfo(  # type: ignore
                        source,
                        destinationFromSource=True,
                    )
                    or []
                )
        else:
            for pose_interpolator in resloved_pose_interpolators:
                target_name = f"{pose_interpolator}.output"
                indices = cmds.getAttr(target_name, multiIndices=True) or []

                for index in indices:
                    destinations.extend(
                        cmds.connectionInfo(  # type: ignore
                            f"{target_name}[{index}]",
                            destinationFromSource=True,
                        )
                        or []
                    )

        for dest in destinations:
            node, target_name = dest.split(".", 1)
            if node == blendshape:
                targets.append(target_name)

        export_maya_shape_file(
            shape_file,
            blendshape,
            targets,
        )
