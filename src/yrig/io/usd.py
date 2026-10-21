from pathlib import Path

from maya import cmds


def import_model_usd(filepath: Path) -> list[str]:
    if not filepath.exists():
        raise FileNotFoundError(f"No file found at {filepath}")
    imported_top_level_prims: list[str] = cmds.mayaUSDImport(  # type: ignore
        file=str(filepath), primPath="/", preferredMaterial="openPBRSurface"
    )
    return imported_top_level_prims
