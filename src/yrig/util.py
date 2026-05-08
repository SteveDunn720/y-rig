from pathlib import Path

from maya import cmds


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
    if confirm == "Yes":
        True
    return False
