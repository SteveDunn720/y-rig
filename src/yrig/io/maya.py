import logging
import tempfile
from collections.abc import Iterable
from pathlib import Path

from maya import cmds

from yrig.io.core import confirm_overwrite
from yrig.select import maintain_selection

log = logging.getLogger(__name__)


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
    log.info(f"Imported Maya file from {filepath}")
    return imported_nodes


# This is a HACK to try and make git diffs of rig build data more helpful.
# Please remove this if Maya adds the ability to export without node UUIDs natively
def _remove_node_uuid_lines(filepath: Path) -> None:
    """Remove node UUID rename commands from a Maya ASCII file."""
    temp_path: Path | None = None
    try:
        # Create temporary file in the same directory
        with tempfile.NamedTemporaryFile(
            "w",
            dir=filepath.parent,
            prefix=f".{filepath.name}.",
            suffix=".tmp",
            delete=False,
            encoding="utf-8",
        ) as destination:
            temp_path = Path(destination.name)
            with filepath.open("r", encoding="utf-8") as source:
                for line in source:
                    if not line.lstrip().startswith("rename -uid "):
                        destination.write(line)

        # Only replace the file if we successfully completed the 'with' block
        temp_path.replace(filepath)
        log.debug(f"Removed node UUID rename lines from Maya ASCII file at {filepath}.")
    except Exception:
        # If anything goes wrong, delete the temp file and leave the original alone
        if temp_path:
            temp_path.unlink(missing_ok=True)
        raise


def export_maya_file(
    filepath: Path,
    nodes: Iterable[str] | None = None,
    binary: bool = False,
    force: bool = False,
    write_node_uuid: bool = False,
) -> bool:
    """Export a Maya scene or a collection of nodes to a Maya file.

    Args:
        filepath: Path to the Maya file to export.
        nodes: Nodes to export. If None, the entire scene is exported.
        binary: Whether to export as a Maya binary file. If False, exports
            as a Maya ASCII file.
        force: Whether to overwrite an existing file without prompting.
        write_node_uuid: When False and exporting Maya ASCII, the file will have all node UUID rename lines stripped from the exported file.

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
            log.info(f"Exported {export_type} file to {filepath}")
    else:
        cmds.file(
            str(filepath),
            exportAll=True,
            type=export_type,
            force=True,
        )
        log.info(f"Exported {export_type} file to {filepath}")
    if not binary and not write_node_uuid:
        _remove_node_uuid_lines(filepath)
    return True
