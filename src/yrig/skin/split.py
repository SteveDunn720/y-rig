from dataclasses import dataclass
from typing import Iterable, Self, Sequence, TypeVar

import maya.cmds as cmds
from maya.api import OpenMaya as om2
from maya.api.OpenMaya import (
    MDagPath,
    MFnNurbsCurve,
    MFnNurbsCurveData,
    MFnNurbsSurface,
    MObject,
    MPoint,
    MPointArray,
    MSelectionList,
)

from yrig import spline
from yrig.math import remap
from yrig.maya_api.attribute import (
    BooleanAttribute,
    IndexableMessageAttribute,
    IntegerAttribute,
    MessageAttribute,
)
from yrig.skin.core import (
    get_mesh_points,
    get_skin_cluster,
    get_skin_cluster_influences,
    get_skin_clusters,
    get_weights,
    set_weights,
)

# CV can be anything: a Vector3, a transform name, etc.
CV = TypeVar("CV")


def get_mesh_spline_weights(
    mesh_shape: str,
    cv_transforms: Sequence[str],
    degree: int = 2,
    periodic: bool = False,
    vertex_indices: list[int] | None = None,
    debug_curve: bool = False,
) -> list[list[tuple[str, float]]]:
    """
    Calculates spline-based weights for each vertex on a mesh relative to a temporary NURBS curve
    defined by a set of CV transforms.

    The function builds a curve from the given transforms, projects each mesh vertex onto the curve
    to compute the closest parameter value, then calculates De Boor-style basis weights using the
    curve's knot vector and degree.

    Args:
        mesh_shape (str): The name of the mesh shape node (not the transform).
        cv_transforms (list[str]): A list of transform names representing the CVs of the curve.
        degree (int, optional): Degree of the spline curve. Defaults to 2.
        periodic: If True will generate a periodic curve for getting spline weights.
        vertex_indices: A list of vertex indices to output weights for.
        debug_curve: If True a curve node will be created for debug purposes.
    Returns:
        list[list[tuple[Any, float]]]: A list of weights per vertex. Each entry is a list of tuples,
        where each tuple contains a CV transform and its corresponding influence weight on the vertex.
    """
    # Create a curve for checking the closest point
    cv_positions: MPointArray = MPointArray()
    for transform in cv_transforms:
        position: tuple[float, float, float] = tuple(
            cmds.xform(  # type: ignore
                transform, query=True, worldSpace=True, translation=True
            )
        )
        cv_positions.append(MPoint(*position))

    extended_cv_positions: MPointArray
    extended_cv_transforms: list[str]
    if periodic:
        extended_cv_positions = MPointArray(cv_positions) + cv_positions[:degree]
        extended_cv_transforms = list(cv_transforms) + list(cv_transforms)[:degree]
    else:
        extended_cv_positions = MPointArray(cv_positions)
        extended_cv_transforms = list(cv_transforms)
    knots: list[float] = spline.generate_knots(
        len(extended_cv_positions), degree=degree, periodic=periodic
    )
    maya_knots: list[float] = knots[1:-1]

    fn_data: MFnNurbsCurveData = om2.MFnNurbsCurveData()
    data_obj: MObject = fn_data.create()
    fn_curve: MFnNurbsCurve = om2.MFnNurbsCurve()
    fn_curve.create(
        extended_cv_positions,
        om2.MDoubleArray(maya_knots),
        degree,
        om2.MFnNurbsCurve.kOpen if not periodic else om2.MFnNurbsCurve.kPeriodic,
        False,  # create2D
        False,  # not rational
        data_obj,
    )

    if debug_curve:
        cmds.curve(
            name=f"{mesh_shape}_SplineWeightsDebugCurve",
            point=[
                (cv_position.x, cv_position.y, cv_position.z)
                for cv_position in extended_cv_positions
            ],
            periodic=periodic,
            knot=maya_knots,
            degree=degree,
            worldSpace=True,
        )

    # get the MDagPaths
    msel: om2.MSelectionList = om2.MSelectionList()
    msel.add(mesh_shape)
    mesh_dag: om2.MDagPath = msel.getDagPath(0)

    # make the function set and get the points
    fn_mesh: om2.MFnMesh = om2.MFnMesh(mesh_dag)

    # get the points in world space

    mesh_points: MPointArray = get_mesh_points(fn_mesh=fn_mesh, vertex_indices=vertex_indices)

    # iterate over the points and get the closest parameter
    parameters: list[float] = []
    for i, point in enumerate(mesh_points):  # type: ignore
        parameter: float = fn_curve.closestPoint(point, space=om2.MSpace.kObject)[1]
        parameters.append(parameter)

    spline_weights_per_vertex: list[list[tuple[str, float]]] = spline.get_weights_along_spline(
        cvs=extended_cv_transforms, parameters=parameters, degree=degree, knots=knots
    )

    return spline_weights_per_vertex


def get_mesh_surface_weights(
    mesh_shape: str,
    surface_shape: str,
    influence_transforms: Sequence[CV],
    degree: int = 2,
    vertex_indices: list[int] | None = None,
) -> list[list[tuple[CV, float]]]:
    """
    Calculates weights for each vertex on a mesh relative to a given NURBS surface.

    The function projects each mesh vertex onto the surface to compute the closest parameter value,
    then calculates De Boor basis weights using the parameter.

    Args:
        mesh_shape (str): The name of the mesh shape node (not the transform).
        surface_shape (str): The name of the NUBRS surface shape node to use for weights splitting.
        influence_transforms (list[str]): A list of transform names that the weights need to be split along.
        degree (int, optional): Degree of the spline curve. Defaults to 2.
        vertex_indices: A list of vertex indices to output weights for.
    Returns:
        list[list[tuple[Any, float]]]: A list of weights per vertex. Each entry is a list of tuples,
        where each tuple contains a influence transform and its corresponding influence weight on the vertex.
    """
    msel: MSelectionList = MSelectionList()
    msel.add(mesh_shape)
    msel.add(surface_shape)
    mesh_dag: MDagPath = msel.getDagPath(0)
    surface_dag: MDagPath = msel.getDagPath(1)

    # make the function sets and data on the surface
    fn_mesh: om2.MFnMesh = om2.MFnMesh(mesh_dag)
    fn_surface = MFnNurbsSurface(surface_dag)
    surface_v_range: tuple[float, float] = cmds.getAttr(f"{surface_shape}.minMaxRangeV")[0]

    # get the points in world space
    mesh_points: MPointArray = get_mesh_points(fn_mesh=fn_mesh, vertex_indices=vertex_indices)

    # iterate over the points and get the closest parameter
    parameters: list[float] = []
    for i, point in enumerate(mesh_points):  # type: ignore
        parameter: float = fn_surface.closestPoint(point, space=om2.MSpace.kObject)[2]
        new_parameter = remap(
            input=parameter,
            input_range=(surface_v_range),
            output_range=(0, len(influence_transforms)),
        )
        parameters.append(new_parameter)

    spline_weights_per_vertex: list[list[tuple[CV, float]]] = spline.get_weights_along_spline(
        cvs=influence_transforms, parameters=parameters, degree=degree
    )

    return spline_weights_per_vertex


@dataclass
class WeightSplitData:
    """Describes how a single influence's weights should be split across multiple joints."""

    source_influence: str
    split_influences: list[str]
    degree: int = 2
    periodic: bool = False


class WeightSplitTag:
    def __init__(self, node: str):
        self.source_influence = MessageAttribute(f"{node}.source_influence")
        self.degree = IntegerAttribute(f"{node}.degree")
        self.periodic = BooleanAttribute(f"{node}.periodic")
        self.split_influences = IndexableMessageAttribute(f"{node}.split_influences")

    @classmethod
    def create(cls, name: str | None) -> Self:
        tag_node = cmds.createNode("network", name=name if name is not None else "weight_split_tag")
        cmds.addAttr(
            tag_node,
            longName="source_influence",
            attributeType="message",
        )
        cmds.addAttr(
            tag_node,
            longName="degree",
            attributeType="long",
        )
        cmds.addAttr(
            tag_node,
            longName="periodic",
            attributeType="bool",
        )
        cmds.addAttr(tag_node, longName="split_influences", attributeType="message", multi=True)

        return cls(tag_node)

    @classmethod
    def from_node(cls, node: str) -> Self | None:
        if not cmds.objExists(node):
            return None
        return cls(node)

    def get_weight_split_data(self) -> WeightSplitData:
        destinations = self.source_influence.connected_nodes(source=False, destination=True)
        if not destinations:
            raise RuntimeError(
                f"{self.source_influence} doesn't have a connection to an influence, maybe it was disconnected at some point?"
            )

        degree = self.degree.value
        periodic = self.periodic.value
        split_influences = [
            split_influence_attr.source_node
            for split_influence_attr in self.split_influences
            if split_influence_attr.source_node is not None
        ]

        return WeightSplitData(
            source_influence=destinations[0],
            split_influences=split_influences,
            degree=degree,
            periodic=periodic,
        )


def tag_for_weight_split(
    influence: str, split_influences: Sequence[str], degree: int = 2, periodic: bool = False
) -> WeightSplitTag:
    """Create a tag connected to an influence joint with metadata attributes describing how its weights should be split.
    This data can later be read back with `get_weight_split_data` to drive an automated weight-split operation.

    Args:
        influence: The influence joint node that will be tagged.
        split_influences: An ordered sequence of joint/transform names that the influence's
            weights should be redistributed across.
        degree: Degree of the spline used for spatial weight interpolation. Defaults to 2.
        periodic: If ``True``, the generated spline curve will be periodic. Defaults to ``False``.
    """
    cmds.addAttr(
        influence,
        longName="weight_split_tag",
        attributeType="message",
    )
    tag_node = WeightSplitTag.create(name=f"{influence}_weight_split_tag")
    tag_node.source_influence.connect_to(f"{influence}.weight_split_tag")
    tag_node.degree.set(degree)
    tag_node.periodic.set(periodic)
    for i, split_influence in enumerate(split_influences):
        tag_node.split_influences[i].connect_from(f"{split_influence}.message")
    return tag_node


def get_weight_split_tag(influence: str) -> WeightSplitTag | None:
    if not cmds.objExists(f"{influence}.weight_split_tag"):
        return None
    sources = cmds.listConnections(f"{influence}.weight_split_tag", source=True, destination=False)
    if not sources:
        return None
    source = sources[0]
    return WeightSplitTag.from_node(source)


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
    mesh_shape: str = cmds.listRelatives(mesh, shapes=True)[0]

    # get the skinCluster and weights
    split_skin_cluster = skin_cluster if skin_cluster is not None else get_skin_cluster(mesh)
    original_weights: dict[int, dict[str, float]] = get_weights(
        shape=mesh_shape, skin_cluster=split_skin_cluster
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

    set_weights(
        shape=mesh_shape, new_weights=new_weights, skin_cluster=split_skin_cluster, normalize=True
    )


def auto_split_weights(meshes: Iterable[str] | str) -> None:
    meshes_to_split = (meshes,) if isinstance(meshes, str) else meshes
    for mesh in meshes_to_split:
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
                print(f"Finished splitting {skin_cluster} weights on {mesh}.")
