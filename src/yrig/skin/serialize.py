import logging
from dataclasses import dataclass
from pathlib import Path

from yrig.io import confirm_overwrite
from yrig.io.json import export_json, load_json
from yrig.shape import get_shape
from yrig.skin.core import (
    get_skin_cluster,
    get_skin_cluster_influences,
    get_skin_weights,
    set_skin_weights,
)

log = logging.getLogger(__name__)


@dataclass
class SkinWeightData:
    influences: list[str]
    skin_weights: dict[int, dict[str, float]]


def skin_weight_data_from_file(filepath: Path) -> SkinWeightData:
    return load_json(filepath, SkinWeightData)


def apply_skin_weight_data(
    data: SkinWeightData, geometry: str, skin_cluster: str | None = None
) -> str:
    """
    Apply SkinWeightData to the skinCluster on the given geometry.

    Args:
        data: SkinWeightData object.
        geometry: Target mesh or transform to apply weights to.
        skin_cluster: Optional specification of which skinCluster node.

    Returns:
        str: The name of the skinCluster that the weights were applied to.
    """
    shape = get_shape(geometry)
    if shape is None:
        raise RuntimeError(f"{geometry} has no attached shape node")
    applied_skin_cluster = set_skin_weights(shape, data.skin_weights, skin_cluster=skin_cluster)
    return applied_skin_cluster


def export_skin_weights(
    filepath: Path, geometry: str, skin_cluster: str | None = None, force: bool = False
) -> bool:
    """
    Export skin weights from a geometry's skinCluster to a file.

    The output file will be JSON, but should have the `.yskin` extension.

    Args:
        filepath: Destination path (should use `.yskin` extension).
        geometry: Mesh or transform containing the skinned geometry.
        skin_cluster: Optional specification of which skinCluster node.
        force: If True, overwrite existing files without prompting.

    Returns:
        True if export succeeded, False if aborted due to overwrite check.
    """
    if filepath.suffix != ".yskin":
        raise ValueError("Skin weight files should use the .yskin extension.")
    if not skin_cluster:
        resolved_skin_cluster = get_skin_cluster(geometry)
        if not resolved_skin_cluster:
            raise RuntimeError(f"No skinCluster on {geometry}")
    else:
        resolved_skin_cluster = skin_cluster

    if not confirm_overwrite(filepath, force):
        return False

    skin_weights = get_skin_weights(geometry, skin_cluster)
    influences = get_skin_cluster_influences(resolved_skin_cluster)
    skin_weight_data = SkinWeightData(influences=influences, skin_weights=skin_weights)
    export_json(filepath, skin_weight_data)
    log.info(f"The skin weights for {resolved_skin_cluster} were written to {filepath}")
    return True


def import_skin_weights(filepath: Path, geometry: str, skin_cluster: str | None = None) -> str:
    """
    Import skin weights from a file and apply them to the skinCluster on the given geometry.
    The input file must be a `.yskin` JSON-based skin weight file produced by yrig.

    Args:
        filepath: Path to `.yskin` skin weight file.
        geometry: Target mesh or transform to apply weights to.
        skin_cluster: Optional specification of which skinCluster node.

    Raises:
        FileNotFoundError: If the `.yskin` file does not exist.
        RuntimeError: If geometry has no valid shape node or cannot be resolved.

    Returns:
        str: The name of the skinCluster that the weights were applied to.
    """
    skin_weight_data = skin_weight_data_from_file(filepath)
    shape = get_shape(geometry)
    if shape is None:
        raise RuntimeError(f"{geometry} has no shape and can't be skinned.")
    applied_skin_cluster = set_skin_weights(
        shape, skin_weight_data.skin_weights, skin_cluster=skin_cluster
    )
    log.info(f"Skin weights applied to {applied_skin_cluster} from {filepath}")
    return applied_skin_cluster
