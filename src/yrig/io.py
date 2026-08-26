from collections.abc import Iterable
from pathlib import Path

from maya import cmds

from yrig.select import maintain_selection


def confirm_overwrite(filepath: Path, force: bool = False) -> bool:
    """
    If *filepath* does not exist, return ``True`` immediately.

    If *filepath* already exists, show a confirmation dialogue and return
    ``True`` only if the user explicitly agrees to overwrite or if *force* is ``True``.
    """
    if filepath.is_dir():
        raise IsADirectoryError(f"Found directory instead of file at {filepath}")
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
    export_suffix = ".mb" if binary else ".ma"
    export_type = "mayaBinary" if binary else "mayaAscii"

    if export_suffix != filepath.suffix:
        raise ValueError(f"Wrong file extension for {export_type}: {export_suffix} : {filepath}")
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
            exportAll=True,
            type=export_type,
            force=True,
        )
    return True
