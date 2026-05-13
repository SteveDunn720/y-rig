from itertools import zip_longest
from typing import Iterable

from maya import cmds
from maya.api.OpenMaya import MDagPath, MFnNurbsSurface, MPoint, MSelectionList, MSpace

from yrig.math import remap
from yrig.maya_api.enum import Axis
from yrig.maya_api.node import (
    ClosestPointOnSurfaceNode,
    MultiplyPointByMatrixNode,
    MultMatrixNode,
    UvPinNode,
)
from yrig.name import get_short_name
from yrig.transform import get_shape
from yrig.transform.matrix import drive_transform_with_matrix
from yrig.transform.structs import Direction
from yrig.transform.utils import get_position


def closest_point_on_surface(
    surface: str, position: MPoint | tuple[float, float, float], world_space: bool = True
) -> tuple[MPoint, tuple[float, float]]:
    """
    Return the closest point and UV on a NURBS surface to the given position.

    Args:
        surface: The NURBS surface transform or shape.
        position: Query point.

    Returns:
        Tuple of (closest point, (u, v)) in object space.
    """
    shape = get_shape(surface)
    msel: MSelectionList = MSelectionList()
    msel.add(shape)
    surface_dag: MDagPath = msel.getDagPath(0)
    fn_surface: MFnNurbsSurface = MFnNurbsSurface(surface_dag)

    test_point: MPoint = position if isinstance(position, MPoint) else MPoint(*position)

    result_point, u, v = fn_surface.closestPoint(
        test_point, space=MSpace.kWorld if world_space else MSpace.kObject
    )
    return (result_point, (u, v))


def surface_uv_domain(surface: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """
    Return the knot domain of a NURBS surface in U and V.
    (minimum and maximum UV parameter values for the surface)

    Args:
        surface: The NURBS surface transform or shape.

    Returns:
        Tuple of ((u_min, u_max), (v_min, v_max)).
    """
    shape = get_shape(surface)
    msel: MSelectionList = MSelectionList()
    msel.add(shape)
    surface_dag: MDagPath = msel.getDagPath(0)
    fn_surface: MFnNurbsSurface = MFnNurbsSurface(surface_dag)
    return (fn_surface.knotDomainInU, fn_surface.knotDomainInV)


def _get_surface_shapes(surface: str) -> tuple[str, str, str]:
    """Return (primary_shape, original_shape, shape_output_attr)."""
    shapes: list[str] = cmds.listRelatives(surface, shapes=True, noIntermediate=True) or []
    if not shapes:
        cmds.error(f"No shape nodes found on surface: {surface}")
    primary_shape: str = shapes[0]
    original_shape_geo: str = cmds.deformableShape(primary_shape, originalGeometry=True)[0]  # type: ignore
    if not original_shape_geo:
        original_shape_geo = cmds.deformableShape(primary_shape, createOriginalGeometry=True)  # type: ignore
    # the return from deformableShape is in the form ["shapeName.local"] so we pull the node name with a split
    original_shape: str = original_shape_geo.split(".", 1)[0]
    shape_output: str = cmds.deformableShape(primary_shape, worldShapeOutAttr=True)[0]  # type: ignore

    return primary_shape, original_shape, shape_output


def _resolve_uv_for_pin(
    surface: str, object_to_pin: str, uv: tuple[float, float] | None = None, normalize: bool = False
) -> tuple[float, float]:
    if uv is not None:
        resolved_uv = uv
    else:
        object_to_pin_position = get_position(object_to_pin)
        _, sampled_uv = closest_point_on_surface(surface, object_to_pin_position)
        if normalize:
            surface_domain_u, surface_domain_v = surface_uv_domain(surface)
            remapped_u = remap(sampled_uv[0], surface_domain_u)
            remapped_v = remap(sampled_uv[1], surface_domain_v)
            resolved_uv = (remapped_u, remapped_v)
        else:
            resolved_uv = sampled_uv

    return resolved_uv


def uv_pin(
    surface: str,
    object_to_pin: str,
    uv: tuple[float, float] | None = None,
    normalize: bool = False,
    normal_axis: Axis | Direction = Axis.Z,
    tangent_axis: Axis | Direction = Axis.X,
    uv_pin_node: UvPinNode | None = None,
) -> UvPinNode:
    """
    Create a uvPin node that pins an object to a given surface at specified UV coordinates.

    Args:
        surface: The name of the surface (mesh or NURBS) to pin to.
        object_to_pin: The name of the object to be pinned.
        uv: The UV coordinate to pin at, if None it will be pinned to the closest point.
        When false, the pinned object has inheritsTransform disabled to prevent double transforms.
        normalize: Enable Isoparm normalization (NURBS UV will be remapped between 0-1).
        normal_axis: Normal axis of the generated uvPin, can be x y z -x -y -z.
        tangent_axis: Tangent axis of the generated uvPin, can be x y z -x -y -z.
        uv_pin_node: When specified the object will be pinned as an additional slot in the given uvPin node.
    Returns:
        The created UVPin node.
    """

    primary_shape, original_shape, shape_output = _get_surface_shapes(surface)
    pin_name = f"{get_short_name(object_to_pin)}_uvPin"

    if uv_pin_node is None:
        # Create the UVPin node and connect it.
        uv_pin_node = UvPinNode(pin_name)
        uv_pin_node.original_geometry.connect_from(f"{original_shape}.{shape_output}")
        uv_pin_node.deformed_geometry.connect_from(f"{primary_shape}.{shape_output}")
        index = 0
    else:
        uv_pin_node = uv_pin_node
        pin_indices = uv_pin_node.coordinate.get_indices()
        index = 0
        while index in pin_indices:
            index += 1

    normal_axis_enum = normal_axis if isinstance(normal_axis, Axis) else Axis.from_str(normal_axis)
    tangent_axis_enum = (
        tangent_axis if isinstance(tangent_axis, Axis) else Axis.from_str(tangent_axis)
    )

    uv_pin_node.normal_axis.set(normal_axis_enum)
    uv_pin_node.tangent_axis.set(tangent_axis_enum)
    uv_pin_node.normalized_isoparms.set(normalize)

    resolved_uv = _resolve_uv_for_pin(primary_shape, object_to_pin, uv, normalize)
    uv_pin_node.coordinate[index].set(resolved_uv)

    localize_matrix = MultMatrixNode(f"{pin_name}_localize")
    localize_matrix.matrix_in[0].connect_from(uv_pin_node.output_matrix[index])
    localize_matrix.matrix_in[1].connect_from(f"{object_to_pin}.parentInverseMatrix[0]")
    drive_transform_with_matrix(localize_matrix.matrix_sum, object_to_pin, scale=False, shear=False)
    return uv_pin_node


def add_to_uv_pin(
    uv_pin_node: UvPinNode, object_to_pin: str, uv: tuple[float, float] | None = None
) -> None:
    pass


def uv_pin_multi(
    name: str,
    surface: str,
    objects_to_pin: Iterable[str],
    uv_coords: Iterable[tuple[float, float]] | None = None,
    normalize: bool = False,
    normal_axis: Axis | Direction = Axis.Z,
    tangent_axis: Axis | Direction = Axis.X,
) -> UvPinNode:

    primary_shape, original_shape, shape_output = _get_surface_shapes(surface)
    pin_name = f"{name}_uvPin"
    uv_pin_node = UvPinNode(pin_name)
    uv_pin_node.original_geometry.connect_from(f"{original_shape}.{shape_output}")
    uv_pin_node.deformed_geometry.connect_from(f"{primary_shape}.{shape_output}")

    for object_to_pin, uv in zip_longest(
        objects_to_pin, uv_coords if uv_coords else (), fillvalue=None
    ):
        if object_to_pin is None:
            raise ValueError(f"More uv_coordinates than objects_to_pin. Unable to pin.")
        uv_pin(
            surface,
            object_to_pin,
            uv=uv,
            normalize=normalize,
            normal_axis=normal_axis,
            tangent_axis=tangent_axis,
            uv_pin_node=uv_pin_node,
        )

    return uv_pin_node


def surface_slide_constraint(
    surface: str,
    driver_transform: str,
    slider_transform: str,
    normal_axis: tuple[float, float, float] = (0, 0, 1),
    secondary_axis: tuple[float, float, float] = (0, 1, 0),
) -> None:
    driver_name = get_short_name(driver_transform)
    slider_name = get_short_name(slider_transform)
    closest_point_node = ClosestPointOnSurfaceNode(f"{driver_name}_closestPoint")
    shape = get_shape(surface)
    if shape is None:
        raise ValueError(f"{surface} has no valid shape")
    closest_point_node.input_surface.connect_from(f"{shape}.worldSpace[0]")

    world_driver_pos = MultiplyPointByMatrixNode(f"{driver_name}_world_pos")
    world_driver_pos.input_matrix.connect_from(f"{driver_transform}.worldMatrix[0]")
    closest_point_node.in_position.connect_from(world_driver_pos.output)

    local_slider_pos = MultiplyPointByMatrixNode(f"{slider_name}_local_pos")
    local_slider_pos.input_point.connect_from(closest_point_node.result.position)
    local_slider_pos.input_matrix.connect_from(f"{slider_transform}.parentInverseMatrix[0]")
    local_slider_pos.output.connect_to(f"{slider_transform}.translate")

    cmds.normalConstraint(
        shape,
        slider_transform,
        aimVector=normal_axis,
        upVector=secondary_axis,
        worldUpType="objectrotation",
        worldUpVector=secondary_axis,
        worldUpObject=driver_transform,
    )
