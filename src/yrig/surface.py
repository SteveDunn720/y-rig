from maya import cmds

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


def uv_pin(
    object_to_pin: str,
    surface: str,
    uv: tuple[float, float],
    normalize: bool = False,
    normal_axis: Axis | Direction = Axis.Z,
    tangent_axis: Axis | Direction = Axis.X,
) -> UvPinNode:
    """
    Create a uvPin node that pins an object to a given surface at specified UV coordinates.

    Args:
        object_to_pin: The name of the object to be pinned.
        surface: The name of the surface (mesh or NURBS) to pin to.
        uv: The UV coordinate to pin at.
        When false, the pinned object has inheritsTransform disabled to prevent double transforms.
        normalize: Enable Isoparm normalization (NURBS UV will be remapped between 0-1).
        normal_axis: Normal axis of the generated uvPin, can be x y z -x -y -z.
        tangent_axis: Tangent axis of the generated uvPin, can be x y z -x -y -z.
    Returns:
        The created UVPin node.
    """
    # Retrieve shape nodes from the surface.
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

    pin_name = f"{get_short_name(object_to_pin)}_uvPin"
    # Create the UVPin node and connect it.
    uv_pin = UvPinNode(pin_name)
    uv_pin.original_geometry.connect_from(f"{original_shape}.{shape_output}")
    uv_pin.deformed_geometry.connect_from(f"{primary_shape}.{shape_output}")

    normal_axis_enum = normal_axis if isinstance(normal_axis, Axis) else Axis.from_str(normal_axis)
    tangent_axis_enum = (
        tangent_axis if isinstance(tangent_axis, Axis) else Axis.from_str(tangent_axis)
    )

    uv_pin.normal_axis.set(normal_axis_enum)
    uv_pin.tangent_axis.set(tangent_axis_enum)
    uv_pin.normalized_isoparms.set(normalize)
    uv_pin.coordinate[0].set(uv)

    localize_matrix = MultMatrixNode(f"{pin_name}_localize")
    localize_matrix.matrix_in[0].connect_from(uv_pin.output_matrix[0])
    localize_matrix.matrix_in[1].connect_from(f"{object_to_pin}.parentInverseMatrix[0]")
    drive_transform_with_matrix(localize_matrix.matrix_sum, object_to_pin, scale=False, shear=False)
    return uv_pin


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
    pass
