import logging
from typing import Iterable

from yrig.build.progress import progress_step, progress_update
from yrig.skin.core import (
    get_shape,
    get_skin_cluster,
    get_skin_cluster_influences,
    get_skin_clusters,
    get_skin_weights,
    set_skin_weights,
)
from yrig.skin.split.data import WeightSplitData, get_mesh_spline_weights
from yrig.skin.split.tag import get_weight_split_tag

log = logging.getLogger(__name__)


def split_weights(
    mesh: str,
    split_data_collection: Iterable[WeightSplitData],
    skin_cluster: str | None = None,
) -> None:
    """
    This function is designed to reassign weights from a set of original joints (e.g., proxy drivers)
    across multiple split joints (e.g., spline-based deformation chains like ribbons or bendy limbs).
    The redistribution is done by computing weights along a spline built from the split joints'
    world positions and distributing the original joint's influence accordingly.

    For each `WeightSplitData` entry a temporary NURBS curve is built from the
    world-space positions of the split influences. Every vertex that is affected by the
    source influence is projected onto that curve and assigned new weights via B-spline
    basis evaluation. The source influence's weight is then zeroed out and its value is
    redistributed across the split influences proportionally.

    Args:
        mesh: The transform node or mesh shape.
        split_data_collection: One or more `WeightSplitData` descriptors, each
            specifying a source influence and the ordered list of split
            influences that should receive its weights.  The ``degree`` and ``periodic``
            fields on each descriptor control the spline used for interpolation.
        skin_cluster: Explicit skinCluster node name to operate on.  When ``None``
            the first skinCluster found on *mesh* is used.

    Raises:
        RuntimeError: If no skinCluster can be resolved for *mesh*.
    """
    # get the shape node
    mesh_shape = get_shape(mesh)
    if mesh_shape is None:
        raise RuntimeError(f"{mesh} has no attached shape node")
    # get the skinCluster and weights
    split_skin_cluster = skin_cluster if skin_cluster is not None else get_skin_cluster(mesh)
    original_weights: dict[int, dict[str, float]] = get_skin_weights(
        geometry=mesh_shape, skin_cluster=split_skin_cluster
    )

    # Copy the original weights for modification.
    new_weights: dict[int, dict[str, float]] = {
        vtx: weights.copy() for vtx, weights in original_weights.items()
    }

    # Organize weights by influence rather than vertex
    weights_by_influence: dict[str, dict[int, float]] = {}
    for vertex, influence_weights in original_weights.items():
        for influence, weight in influence_weights.items():
            if influence in weights_by_influence:
                weights_by_influence[influence][vertex] = weight
            else:
                weights_by_influence[influence] = {vertex: weight}

    # Process each original joint → split joints mapping
    for split_data in split_data_collection:
        vertex_weights: dict[int, float] = {}
        source_influence = split_data.source_influence
        if source_influence in weights_by_influence:
            vertex_weights = weights_by_influence[source_influence]

        # Filter for vertices actually influenced by this joint (less inputs for the spline weight algorithm)
        influenced_vertex_weights: list[tuple[int, float]] = []
        influenced_vertices: list[int] = []
        for vertex, weight in vertex_weights.items():
            if weight > 0:
                influenced_vertex_weights.append((vertex, weight))
                influenced_vertices.append(vertex)

        # Skip if no vertices are influenced by this joint
        if not influenced_vertices:
            continue

        # Get spline-based weights for each influenced vertex
        spline_weights: list[list[tuple[str, float]]] = get_mesh_spline_weights(
            mesh_shape=mesh_shape,
            cv_transforms=split_data.split_influences,
            degree=split_data.degree,
            periodic=split_data.periodic,
            vertex_indices=influenced_vertices,
        )

        # Redistribute the weights
        for i, (vertex, original_weight) in enumerate(influenced_vertex_weights):
            # Remove original joint weight
            new_weights[vertex][source_influence] = 0.0

            # Add redistributed weights to split joints
            for influence, spline_weight in spline_weights[i]:
                if influence not in new_weights[vertex]:
                    new_weights[vertex][influence] = 0.0
                new_weights[vertex][influence] += spline_weight * original_weight

    set_skin_weights(
        shape=mesh_shape, weights=new_weights, skin_cluster=split_skin_cluster, normalize=True
    )


def auto_split_weights(meshes: Iterable[str] | str) -> None:
    """Automatically split skin weights on one or more meshes using tagged influences.

    Scans every skinCluster on each mesh for influences that have a
    ``WeightSplitTag`` attached (created via `tag_for_weight_split`).
    For each tagged influence the stored split metadata is read and
    `split_weights` is called to redistribute the weights.

    Args:
        meshes: A single mesh name or an iterable of mesh names to process.
    """
    meshes_to_split = (meshes,) if isinstance(meshes, str) else tuple(meshes)
    with progress_step("Auto Split Weights"):
        total = len(meshes_to_split)
        for i, mesh in enumerate(meshes_to_split):
            skin_clusters: list[str] | None = get_skin_clusters(mesh)
            if skin_clusters is None:
                continue
            for skin_cluster in skin_clusters:
                weight_split_data_list = []
                influences: list[str] = get_skin_cluster_influences(skin_cluster=skin_cluster)
                for influence in influences:
                    weight_split_tag = get_weight_split_tag(influence)
                    if weight_split_tag is None:
                        continue
                    weight_split_data = weight_split_tag.get_weight_split_data()
                    weight_split_data_list.append(weight_split_data)
                if weight_split_data_list:
                    split_weights(
                        mesh,
                        split_data_collection=weight_split_data_list,
                        skin_cluster=skin_cluster,
                    )
                    log.info(f"Finished splitting {skin_cluster} weights on {mesh}.")
            progress_update(i / total)
