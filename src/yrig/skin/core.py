import maya.api.OpenMaya as om2
import maya.cmds as cmds
from maya.api import OpenMayaAnim as oma

from yrig.transform.utils import get_shape


def get_skin_clusters(mesh: str) -> list[str] | None:
    """
    Return all skinCluster deformers in a mesh's construction history.

    Queries the dependency history of the given mesh (transform or shape),
    filters for nodes of type ``skinCluster``, and returns their names.

    Args:
        mesh: The name of a mesh transform or shape node.

    Returns:
        A list of skinCluster node names if any are found, otherwise ``None``.
        The list order reflects the order returned by Maya's history query.
    """
    history = cmds.listHistory(mesh, pruneDagObjects=True) or []
    skin_clusters = cmds.ls(history, type="skinCluster")  # type: ignore
    return skin_clusters if skin_clusters else None


def get_skin_cluster(mesh: str) -> str | None:
    """
    Find the skinCluster deformer attached to a mesh.

    Walks the construction history of the given mesh and returns the first
    ``skinCluster`` node found, or ``None`` if the mesh is not skinned.

    Args:
        mesh: The name of a mesh transform or shape node.

    Returns:
        The name of the first skinCluster node in the mesh's history,
        or ``None`` if no skinCluster is present.
    """
    skin_clusters = get_skin_clusters(mesh)
    return skin_clusters[0] if skin_clusters else None


def get_skin_cluster_influences(skin_cluster: str) -> list[str]:
    """Return the influence joints bound to a skinCluster.

    Args:
        skin_cluster: The name of the skinCluster node to query.

    Returns:
        A list of influence (joint/transform) names associated with the
        skinCluster.
    """
    return cmds.skinCluster(skin_cluster, query=True, influence=True)  # type: ignore


def get_mesh_influences(shape: str, skin_cluster: str | None = None) -> list[str]:
    """Return the influence joints for a mesh's skinCluster.

    Convenience wrapper that resolves the skinCluster from a mesh shape
    (if not provided) and returns its influences.

    Args:
        shape: The name of the mesh shape node.
        skin_cluster: Optional explicit skinCluster node name. When
            ``None``, the first skinCluster in the shape's history is used.

    Returns:
        A list of influence (joint/transform) names.

    Raises:
        RuntimeError: If no skinCluster can be found on *shape*.
    """
    if not skin_cluster:
        skin_cluster: str | None = get_skin_cluster(shape)
        if not skin_cluster:
            raise RuntimeError(f"No skinCluster on {shape}")
    return get_skin_cluster_influences(skin_cluster)


def skin_mesh(
    bind_joints: list[str], geometry: str, name: str | None = None, dual_quaternion: bool = False
) -> str:
    """
    Creates a skinCluster on the given geometry using the specified bind joints.

    Args:
        bind_joints (list[str]): A list of joint names to bind the geometry to.
        geometry (str): The name of the geometry to be skinned.
        name (str | None, optional): The name to assign to the skinCluster.
            If None, a name will be auto-generated based on the geometry name.
        dual_quaternion (bool, optional): Whether to use dual quaternion skinning.
            Defaults to False (classic linear skinning).

    Returns:
        str: The name of the created skinCluster node.
    """
    if not name:
        name = f"{geometry}_SC"

    shape = get_shape(geometry)

    if shape is None:
        raise RuntimeError(
            f"{geometry} is not a shape node! This function expects a transform with a shape or a shape."
        )

    skin_cluster: str = cmds.skinCluster(  # type: ignore
        bind_joints,  # type: ignore
        shape,
        skinMethod=1 if dual_quaternion else 0,
        name=name,
    )

    return skin_cluster


def remove_unused_influences(geometry: str, skin_cluster: str | None = None) -> list[str]:
    """
    Removes unused joints from a skinCluster and returns the removed influences.
    Args:
        geometry: Mesh transform or shape that contains the skinCluster.
        skin_cluster: Optional explicit skinCluster node name. When
            ``None``, the first skinCluster in the shape's history is used.

    Returns:
        List of influence names that were removed from the skinCluster.
    """
    if not skin_cluster:
        skin_cluster: str | None = get_skin_cluster(geometry)
        if not skin_cluster:
            raise RuntimeError(f"No skinCluster on {geometry}")
    original_influences: set[str] = cmds.skinCluster(skin_cluster, query=True, influence=True) or []  # type: ignore
    cmds.skinCluster(skin_cluster, edit=True, removeUnusedInfluence=True)
    new_influences: set[str] = set(cmds.skinCluster(skin_cluster, query=True, influence=True) or [])  # type: ignore
    return [influence for influence in original_influences if influence not in new_influences]


def get_mesh_points(
    fn_mesh: om2.MFnMesh, vertex_indices: list[int] | None = None
) -> om2.MPointArray:
    """Retrieve world-space vertex positions from a mesh function set.

    When *vertex_indices* is ``None`` every vertex position is returned.
    Otherwise only the positions at the requested indices are collected
    (in the order given).

    Args:
        fn_mesh: An ``MFnMesh`` function set already attached to the
            target mesh shape.
        vertex_indices: Optional list of specific vertex indices to
            retrieve. If ``None``, all vertices are returned.

    Returns:
        An ``MPointArray`` containing the requested vertex positions in
        world space.
    """
    mesh_points: om2.MPointArray = om2.MPointArray()
    if vertex_indices is None:
        mesh_points = fn_mesh.getPoints(space=om2.MSpace.kWorld)
        vertex_indices = list(range(len(mesh_points)))
    else:
        all_points: om2.MPointArray = fn_mesh.getPoints(space=om2.MSpace.kWorld)
        for idx in vertex_indices:
            mesh_points.append(all_points[idx])
    return mesh_points


def get_weights_of_influence(skin_cluster: str, joint: str) -> dict[int, float]:
    """Query per-vertex skin weights for a single influence joint.

    Uses the Maya API's ``MFnSkinCluster.getPointsAffectedByInfluence``
    to efficiently retrieve only the vertices and weights associated with
    the given joint.

    Args:
        skin_cluster: The name of the skinCluster node to query.
        joint: The name of the influence joint whose weights are requested.

    Returns:
        A dictionary mapping vertex indices to their weight values for
        the specified joint.  Vertices with zero influence are omitted.
    """
    sel: om2.MSelectionList = om2.MSelectionList()
    sel.add(skin_cluster)
    sel.add(joint)
    skin_cluster_mob: om2.MObject = sel.getDependNode(0)
    joint_dag: om2.MDagPath = sel.getDagPath(1)
    mfn_skin_cluster: oma.MFnSkinCluster = oma.MFnSkinCluster(skin_cluster_mob)

    components: om2.MSelectionList
    weights: list[float]
    components, weights = mfn_skin_cluster.getPointsAffectedByInfluence(joint_dag)

    index_weights: dict[int, float] = {}
    affected_indices: list[int] = []
    for i in range(components.length()):
        dag_path, component = components.getComponent(i)
        fn_comp: om2.MFnSingleIndexedComponent = om2.MFnSingleIndexedComponent(component)
        indices: list[int] = fn_comp.getElements()
        affected_indices.extend(indices)
    for index, weight in zip(affected_indices, weights):
        index_weights[index] = weight

    return index_weights


def set_weights(
    shape: str,
    new_weights: dict[int, dict[str, float]],
    skin_cluster: str | None = None,
    normalize: bool = True,
    clear_old_weights: bool = False,
) -> None:
    """
    Sets skinCluster weights for all vertices of the given mesh shape.

    Args:
        shape (str): The name of the mesh shape node to query. Must have a skinCluster.
        new_weights (dict): Dictionary of vertex weights: {vtx_index: {influence_name: weight}}.
        skin_cluster: Optional specification of which skinCluster node.
        normalize: When True, the given weights will additionally be normalized.
    """
    if not skin_cluster:
        skin_cluster = get_skin_cluster(shape)
        if skin_cluster is None:
            raise RuntimeError(f"No skinCluster on {shape}")

    # Ensure all influences in new_weights exist on the skinCluster
    all_influences_in_data: set[str] = set(
        influence_name
        for vtx_weights in new_weights.values()
        for influence_name in vtx_weights.keys()
    )

    existing_influences = set(cmds.skinCluster(skin_cluster, query=True, influence=True) or [])  # type: ignore

    # Add missing influences to the skinCluster
    influences_to_add: list[str] = sorted(all_influences_in_data - existing_influences)
    if influences_to_add:
        cmds.skinCluster(skin_cluster, edit=True, addInfluence=influences_to_add, weight=0.0)

    # Get the actual MFnSkinCluster to apply weights with
    sel: om2.MSelectionList = om2.MSelectionList()
    sel.add(shape)
    sel.add(skin_cluster)
    sel.add(f"{skin_cluster}.matrix")
    shape_dag: om2.MDagPath = sel.getDagPath(0)
    skin_cluster_mob: om2.MObject = sel.getDependNode(1)
    matrix_list_plug: om2.MPlug = sel.getPlug(2)
    mfn_skin_cluster: oma.MFnSkinCluster = oma.MFnSkinCluster(skin_cluster_mob)

    # Get influence indices
    logical_to_physical: dict[int, int] = {}
    for i in range(matrix_list_plug.numElements()):
        logical_idx = matrix_list_plug.elementByPhysicalIndex(i).logicalIndex()
        logical_to_physical[logical_idx] = i

    influence_paths: om2.MDagPathArray = mfn_skin_cluster.influenceObjects()
    influence_indices: dict[str, int] = {
        om2.MFnDependencyNode(path.node()).name(): logical_to_physical[
            mfn_skin_cluster.indexForInfluenceObject(path)
        ]
        for path in influence_paths
    }

    ordered_influences: list[tuple[str, int]] = list(influence_indices.items())
    ordered_influence_names = [name for name, index in ordered_influences]
    ordered_indices_only = [index for name, index in ordered_influences]
    num_influences: int = len(ordered_influence_names)

    influence_indices_array: om2.MIntArray = om2.MIntArray()
    for index in ordered_indices_only:
        influence_indices_array.append(index)

    # Create vertex component
    num_verts: int = om2.MFnMesh(shape_dag).numVertices
    fn_comp: om2.MFnSingleIndexedComponent = om2.MFnSingleIndexedComponent()
    vtx_components = fn_comp.create(om2.MFn.kMeshVertComponent)
    fn_comp.addElements(list(range(num_verts)))

    # Allocate list for weights
    weights_flat: list[float] = [0.0] * (num_verts * num_influences)

    # Fill weights list from new_weights dict
    for vtx_id, vtx_weights in new_weights.items():
        base_index = vtx_id * num_influences
        for influence_name, weight in vtx_weights.items():
            influence_index = influence_indices[influence_name]
            weights_flat[base_index + influence_index] = weight

    weights_array = om2.MDoubleArray(weights_flat)

    if not mfn_skin_cluster.object().hasFn(om2.MFn.kSkinClusterFilter):
        raise RuntimeError(f"Selected node {skin_cluster} is not a skinCluster")

    # Set weights
    mfn_skin_cluster.setWeights(
        shape_dag,
        vtx_components,
        influence_indices_array,
        weights_array,
        normalize=normalize,
        returnOldWeights=False,
    )


def get_weights(shape: str, skin_cluster: str | None = None) -> dict[int, dict[str, float]]:
    """
    Retrieves skinCluster weights for all vertices of the given mesh shape.

    This function returns the non-zero skin weights per vertex, mapped to their
    associated influence (joint) names. It uses the Maya API to efficiently extract
    weights from the skinCluster deformer attached to the mesh.

    Args:
        shape (str): The name of the mesh shape node to query. Must have a skinCluster.
        skin_cluster: Optional specification of which skinCluster node.

    Returns:
        dict[int, dict[str, float]: A dictionary mapping each vertex index to a list of
        (joint_name, weight) dictionaries, including only non-zero weights.
    """
    if not skin_cluster:
        skin_cluster = get_skin_cluster(shape)
        if not skin_cluster:
            raise RuntimeError(f"No skinCluster on {shape}")

    sel: om2.MSelectionList = om2.MSelectionList()
    sel.add(shape)
    sel.add(skin_cluster)
    sel.add(f"{skin_cluster}.matrix")
    shape_dag: om2.MDagPath = sel.getDagPath(0)
    skin_cluster_mob: om2.MObject = sel.getDependNode(1)
    matrix_list_plug: om2.MPlug = sel.getPlug(2)
    mfn_skin_cluster: oma.MFnSkinCluster = oma.MFnSkinCluster(skin_cluster_mob)

    influence_paths = mfn_skin_cluster.influenceObjects()
    logical_to_physical: dict[int, int] = {}
    for i in range(matrix_list_plug.numElements()):
        logical_idx = matrix_list_plug.elementByPhysicalIndex(i).logicalIndex()
        logical_to_physical[logical_idx] = i
    influence_map = {
        logical_to_physical[mfn_skin_cluster.indexForInfluenceObject(path)]: om2.MFnDependencyNode(
            path.node()
        ).name()
        for path in influence_paths
    }

    # Create vertex component
    num_verts: int = om2.MFnMesh(shape_dag).numVertices
    fn_comp: om2.MFnSingleIndexedComponent = om2.MFnSingleIndexedComponent()
    vtx_components = fn_comp.create(om2.MFn.kMeshVertComponent)
    fn_comp.addElements(list(range(num_verts)))

    flat_weights: list[float]
    influence_count: int
    flat_weights, influence_count = mfn_skin_cluster.getWeights(shape_dag, vtx_components)

    weights_dict: dict[int, dict[str, float]] = {}
    for vtx_id in range(num_verts):
        start_index: int = vtx_id * influence_count
        vtx_weights: dict[str, float] = {}
        for i in range(influence_count):
            weight_value = flat_weights[start_index + i]
            if weight_value > 1e-6:
                influence_name = influence_map.get(i)
                if influence_name:
                    vtx_weights[influence_name] = weight_value
        if vtx_weights:
            weights_dict[vtx_id] = vtx_weights

    return weights_dict


def transfer_skin_weights(
    source: str, target: str, interpolate: bool = True, map_by_name: bool = True
) -> None:
    source_skin: str
    if cmds.nodeType(source) == "skinCluster":
        source_skin = source
    else:
        skin_cluster = get_skin_cluster(source)
        if skin_cluster is None:
            raise RuntimeError(f"No skin cluster found on {source}.")
        source_skin = skin_cluster
    target_skin: str
    if cmds.nodeType(source) == "skinCluster":
        target_skin = source
    else:
        skin_cluster = get_skin_cluster(target)
        if skin_cluster is None:
            raise RuntimeError(f"No skin cluster found on {target}.")
        target_skin = skin_cluster
    cmds.copySkinWeights(
        sourceSkin=source_skin,
        destinationSkin=target_skin,
        noMirror=True,
        smooth=interpolate,
        influenceAssociation="name" if map_by_name else "closestJoint",
    )
