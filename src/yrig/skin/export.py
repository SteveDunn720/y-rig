from __future__ import annotations

from pathlib import Path

import maya.cmds as cmds

from yrig.build.context import get_asset_root
from yrig.skin.core import get_skinned_shapes
from yrig.skin.ng import write_ng_skin_weights
from yrig.skin.serialize import export_skin_weights
from yrig.transform.utils import get_shape
from yrig.util import promt_user_for_directory


def _resolve_export_directory(directory: Path | None = None) -> Path:
    if directory is not None:
        return directory
    if (asset_root := get_asset_root()) is not None:
        return asset_root / "data" / "skin"
    raise RuntimeError(
        "Unable to resolve skin export directory. Provide a directory or set asset root."
    )
    # add in the until function to prompt user to select directory if asset root is not set, or just default to current workspace
    return promt_user_for_directory()


def _get_selected_skin_shapes() -> list[str]:
    selected_nodes = cmds.ls(selection=True, long=True) or []
    if not selected_nodes:
        return []

    skinned_shapes = set(get_skinned_shapes().values())
    selected_shapes: list[str] = []

    for node in selected_nodes:
        if node in skinned_shapes:
            selected_shapes.append(node)
            continue

        shape = get_shape(node)
        if shape and shape in skinned_shapes:
            selected_shapes.append(shape)
            continue

        if cmds.nodeType(node) == "transform":
            child_shapes = (
                cmds.listRelatives(node, shapes=True, noIntermediate=True, fullPath=True) or []
            )
            for child_shape in child_shapes:
                if child_shape in skinned_shapes:
                    selected_shapes.append(child_shape)

    return list(dict.fromkeys(selected_shapes))


def _shape_to_export_name(shape: str) -> str:
    parent = cmds.listRelatives(shape, parent=True, fullPath=True) or []
    if parent:
        return cmds.ls(parent[0], shortNames=True)[0]
    return cmds.ls(shape, shortNames=True)[0]


def _export_weights_for_shape(
    shape: str, directory: Path, use_ng: bool, force: bool
) -> Path | None:
    filepath = directory / f"{_shape_to_export_name(shape)}{'.json' if use_ng else '.yskin'}"

    if use_ng:
        write_ng_skin_weights(filepath=filepath, geometry=shape, force=force)
        return filepath

    if not export_skin_weights(filepath=filepath, geometry=shape, force=force):
        return None

    return filepath


def export_skin_weights_for_shape(
    shape: str,
    directory: Path | None = None,
    use_ng: bool = True,
    force: bool = False,
) -> Path:
    """Export skin weights for a single mesh shape.

    Args:
        shape: The mesh shape node to export weights for.
        directory: Optional directory to write the skin file into.
        use_ng: If True, export ngSkinTools JSON (``.json``). If False, export
            yrig skin file (``.yskin``).
        force: When True, overwrite existing files without prompting.

    Returns:
        The path of the file written.
    """
    export_directory = _resolve_export_directory(directory)
    export_directory.mkdir(parents=True, exist_ok=True)

    exported_path = _export_weights_for_shape(
        shape=shape, directory=export_directory, use_ng=use_ng, force=force
    )
    if exported_path is None:
        raise RuntimeError(f"Export aborted for shape {shape}")
    return exported_path


def export_skin_weights_for_selected(
    directory: Path | None = None,
    use_ng: bool = True,
    force: bool = False,
) -> list[Path]:
    """Export skin weights for the currently selected skinned shapes."""
    shapes = _get_selected_skin_shapes()
    if not shapes:
        raise RuntimeError("No selected skinned geometry found for export.")

    export_directory = _resolve_export_directory(directory)
    export_directory.mkdir(parents=True, exist_ok=True)

    exported_files: list[Path] = []
    for shape in shapes:
        exported_path = _export_weights_for_shape(
            shape=shape, directory=export_directory, use_ng=use_ng, force=force
        )
        if exported_path is not None:
            exported_files.append(exported_path)

    return exported_files


def batch_export_skin_weights(
    directory: Path | None = None,
    selected_only: bool = False,
    use_ng: bool = True,
    force: bool = False,
) -> list[Path]:
    """Export skin weights for selected geometry or all skinned geometry in the scene.

    Args:
        directory: Optional directory to write skin files into.
        selected_only: If True, export only skin weights for currently selected geometry.
        use_ng: If True, export ngSkinTools JSON files (``.json``). If False, export
            yrig skin files (``.yskin``).
        force: When True, overwrite existing files without prompting.

    Returns:
        A list of paths for files that were written.
    """
    export_directory = _resolve_export_directory(directory)
    export_directory.mkdir(parents=True, exist_ok=True)

    shapes = _get_selected_skin_shapes() if selected_only else list(get_skinned_shapes().values())
    if not shapes:
        raise RuntimeError(
            "No selected skinned geometry found for export."
            if selected_only
            else "No skinned geometry found in the scene to export."
        )

    exported_files: list[Path] = []
    for shape in shapes:
        exported_path = _export_weights_for_shape(
            shape=shape, directory=export_directory, use_ng=use_ng, force=force
        )
        if exported_path is not None:
            exported_files.append(exported_path)

    return exported_files
