from pathlib import Path

from maya import cmds


def import_model_usd(filepath: Path, instances: bool = False) -> list[str]:
    if not filepath.exists():
        raise FileNotFoundError(f"No file found at {filepath}")
    imported_top_level_prims: list[str] = cmds.mayaUSDImport(  # type: ignore
        file=str(filepath),
        primPath="/",
        preferredMaterial="openPBRSurface",
        importInstances=instances,
    )
    return imported_top_level_prims
