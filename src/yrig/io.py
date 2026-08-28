import logging
from collections.abc import Iterable
from pathlib import Path

from maya import cmds

from yrig.name import get_short_name
from yrig.select import maintain_selection

log = logging.getLogger(__name__)

SPLIT_PARENT_ATTR = "split_parent"


def confirm_overwrite(filepath: Path, force: bool = False) -> bool:
    """
    If *filepath* does not exist, return ``True`` immediately.

    If *filepath* already exists, show a confirmation dialogue and return
    ``True`` only if the user explicitly agrees to overwrite or if *force* is ``True``.
    """
    if force:
        return True
    if not filepath.exists():
        return True
    confirm: str = cmds.confirmDialog(
        title="File Overwrite",
        message=f"{filepath} already exists and will be overwritten, are you sure you want to write the file?",
        button=["Yes", "No"],
        defaultButton="Yes",
        cancelButton="No",
        dismissString="No",
    )
    return confirm == "Yes"


def promt_user_for_directory(message: str = "Select Directory") -> Path:
    """Prompt the user to select a directory and return it as a Path object."""
    result = cmds.fileDialog2(fileMode=3, dialogStyle=2, caption=message)
    if result and len(result) > 0:
        return Path(result[0])
    else:
        raise RuntimeError("No directory selected.")


def import_maya_file(filepath: Path, keep_namespace: bool = False) -> list[str]:
    """Import a Maya file and return the nodes created by the import.

    Args:
        filepath: Path to the Maya file to import.
        keep_namespace: Whether to preserve the namespace stored in the
            imported file. If False, imported nodes use the default namespace.

    Returns:
        The names of nodes created by the import.
    """
    if not filepath.exists():
        raise FileNotFoundError(f"No maya file was found at {filepath}")
    if filepath.is_dir():
        raise IsADirectoryError(f"Found directory instead of file at {filepath}")
    try:
        imported_nodes: list[str] = cmds.file(  # type: ignore
            str(filepath), i=True, defaultNamespace=not keep_namespace, returnNewNodes=True
        )
    except RuntimeError as exc:
        raise RuntimeError(f"Failed to import the maya file at {filepath}") from exc
    return imported_nodes


def export_maya_file(
    filepath: Path, nodes: Iterable[str] | None = None, binary: bool = False, force: bool = False
) -> bool:
    """Export a Maya scene or a collection of nodes to a Maya file.

    Args:
        filepath: Path to the Maya file to export.
        nodes: Nodes to export. If None, the entire scene is exported.
        binary: Whether to export as a Maya binary file. If False, exports
            as a Maya ASCII file.
        force: Whether to overwrite an existing file without prompting.

    Returns:
        True if the file was exported, or False if the export was cancelled or failed.
    """
    if not confirm_overwrite(filepath, force):
        return False
    export_type = "mayaBinary" if binary else "mayaAscii"
    if nodes is not None:
        with maintain_selection():
            cmds.select(*nodes, replace=True)
            cmds.file(
                str(filepath),
                exportSelected=True,
                type=export_type,
                force=True,
            )
    else:
        cmds.file(
            str(filepath),
            exportSelected=False,
            type=export_type,
            force=True,
        )
    return True


def _add_split_parent_attr(node: str) -> None:
    """Store the node's parent name for later restoration."""

    parent = cmds.listRelatives(
        node,
        parent=True,
        fullPath=False,
    )

    if not parent:
        return

    if not cmds.attributeQuery(
        SPLIT_PARENT_ATTR,
        node=node,
        exists=True,
    ):
        cmds.addAttr(
            node,
            longName=SPLIT_PARENT_ATTR,
            dataType="string",
        )

    cmds.setAttr(
        f"{node}.{SPLIT_PARENT_ATTR}",
        parent[0],
        type="string",
    )


def split_scene_to_files(
    directory: Path,
    objects: Iterable[str],
    remainder_name: str = "remainder",
    binary: bool = False,
    force: bool = False,
) -> bool:
    """Split a Maya scene into seperate exports

    Args:
        output_directory: Path to the folder to export.
        objects: Nodes to split.
        remainder_name: what the main file export will be called
        binary: Whether to export as a Maya binary file. If False, exports
            as a Maya ASCII file.
        force: Whether to overwrite an existing file without prompting.

    Returns:
        True if the file was exported, or False if the export was cancelled or failed.
    """

    cmds.undoInfo(openChunk=True)

    try:
        # Validate split objects
        for obj in objects:
            if not cmds.objExists(obj):
                raise RuntimeError(f"Cannot split scene: '{obj}' does not exist.")

            exported_files: list[Path] = []

            _add_split_parent_attr(obj)

            parent = cmds.listRelatives(
                obj,
                parent=True,
                fullPath=False,
            )

            if parent:
                # Temporarily move object to world
                cmds.parent(obj, world=True)

            extension = ".mb" if binary else ".ma"

            filepath = directory / f"{obj}{extension}"

            export_maya_file(
                filepath=filepath,
                nodes=[obj],
                binary=binary,
                force=force,
            )

        cmds.delete(objects)  # type:ignore
        # Get everything remaining at the top level
        remaining_roots = (
            cmds.ls(
                assemblies=True,
                long=True,
            )
            or []
        )

        remainder_filepath = directory / f"{remainder_name}{extension}"

        exported = export_maya_file(
            filepath=remainder_filepath,
            nodes=remaining_roots,
            binary=binary,
            force=force,
        )

        if exported:
            exported_files.append(remainder_filepath)

    finally:
        cmds.undoInfo(closeChunk=True)
        cmds.undo()

    return True


def import_split_scene_files(
    directory: Path,
    objects: Iterable[str],
    remainder_name: str = "remainder",
    binary: bool = False,
) -> bool:
    """Import a split Maya scene and restore the original hierarchy.

    Args:
        directory: Path to the folder containing the split files.
        objects: Names of the split objects/files to import.
        remainder_name: Name of the main Maya file.
        binary: Whether the files are Maya binary files.

    Returns:
        True if all files were imported successfully.
    """

    extension = ".mb" if binary else ".ma"

    # Import the main scene first
    remainder_filepath = directory / f"{remainder_name}{extension}"

    import_maya_file(
        filepath=remainder_filepath,
    )

    # Import each split object
    for obj in objects:
        filepath = directory / f"{obj}{extension}"

        imported_nodes = import_maya_file(
            filepath=filepath,
        )

        # Find the imported node carrying our split metadata
        for node in imported_nodes:
            node = get_short_name(node)

            if not cmds.attributeQuery(
                SPLIT_PARENT_ATTR,
                node=node,
                exists=True,
            ):
                continue

            parent = cmds.getAttr(f"{node}.{SPLIT_PARENT_ATTR}")

            if parent:
                if cmds.objExists(parent):
                    cmds.parent(node, parent)
                else:
                    log.warning(
                        f"Could not restore parent for '{node}'. Parent '{parent}' does not exist."
                    )

            cmds.deleteAttr(f"{node}.{SPLIT_PARENT_ATTR}")

    return True
