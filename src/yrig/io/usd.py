from pathlib import Path

from maya import cmds


def import_model_usd(filepath: Path, instances: bool = False) -> list[str]:
    if not filepath.exists():
        raise FileNotFoundError(f"No file found at {filepath}")
    kwargs = {}
    if instances:
        kwargs["importInstances"] = True
    imported_top_level_prims: list[str] = cmds.mayaUSDImport(  # type: ignore
        file=str(filepath), primPath="/", preferredMaterial="openPBRSurface", **kwargs
    )
    return imported_top_level_prims
