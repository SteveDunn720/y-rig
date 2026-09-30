import logging
from collections.abc import Iterable
from pathlib import Path

from yrig.io import confirm_overwrite
from yrig.io.json import export_json, load_json

from .apply import apply_pose_interpolator_directory_data
from .data import PoseInterpolatorFileData
from .get import get_pose_interpolator_directory_data

log = logging.getLogger(__name__)


def import_pose_file(
    filepath: Path,
    *,
    directories: Iterable[str] | None = None,
    pose_interpolators: Iterable[str] | None = None,
    parent_directory: str | None = None,
    create_folders: bool = True,
    parent: str | None = None,
) -> None:
    """
    Import poseInterpolator data from a `.ypose` file.

    Args:
        filepath: Source `.ypose` file containing serialized poseInterpolator data.
        directories: Specify poseInterpolator directories to import.
        pose_interpolators: Specify poseInterpolator names to import.
    """
    data = load_json(filepath, PoseInterpolatorFileData)
    apply_pose_interpolator_directory_data(
        data.directory,
        directories=directories,
        pose_interpolators=pose_interpolators,
        parent_directory=parent_directory,
        create_folders=create_folders,
        parent=parent,
    )
    log.info(f"Imported pose file from {filepath}")


def export_pose_file(
    filepath: Path,
    *,
    directories: Iterable[str] | None = None,
    pose_interpolators: Iterable[str] | None = None,
    force: bool = False,
) -> bool:
    """
    Export poseInterpolator data to a `.ypose` file.

    Args:
        filepath: Destination `.ypose` file.

        directories: Specify poseInterpolator directories to import.
        pose_interpolators: Specify poseInterpolator names to export.
        parent_directory: Parent directory for the specified directories and poseInterpolators,
            or the directory to parent the entire imported structure on if neither are specified.
        force: Whether to overwrite an existing file without confirmation.

    Returns:
        ``True`` if the file exported, or ``False``
        if the export was cancelled."""
    if filepath.suffix != ".ypose":
        raise ValueError("Pose Interpolator files should use the .ypose extension.")
    if not confirm_overwrite(filepath, force):
        return False
    directory_data = get_pose_interpolator_directory_data(
        directories=directories, pose_interpolators=pose_interpolators
    )
    file_data = PoseInterpolatorFileData(directory=directory_data)
    export_json(filepath, file_data, compact=False)
    log.info(f"Exported pose file to {filepath}")
    return True
