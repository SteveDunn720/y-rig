from maya import cmds

from yrig.control.serialize import ControlShape, get_curve_data
from yrig.transform import get_shapes


def create_curve(
    name: str | None = None,
    control_shape: ControlShape | str = ControlShape.CIRCLE,
    parent: str | None = None,
) -> str:
    """
    Creates a curve from the specified item in the shape library.

    Args:
        curve_shape(ControlShape): Name of the control shape to generate.
    Returns:
        str: Name of the generated curve transform.
    """
    if isinstance(control_shape, str):
        control_shape: ControlShape = ControlShape[control_shape.strip().upper()]
    curve_data = get_curve_data(curve_shape=control_shape)

    curve_transform: str = cmds.group(empty=True, name=control_shape.value)

    for index, named_curve in enumerate(curve_data.curves):
        curve = named_curve.curve
        positions: list[tuple[float, float, float]] = curve.cv_positions
        degree: int = curve.degree
        periodic: bool = True if curve.form == 2 else False
        knots: list[float] = curve.knots
        weights: list[float] = curve.cv_weights
        position_weights: list[tuple[float, float, float, float]] = [
            (position[0], position[1], position[2], weights[index])
            for index, position in enumerate(positions)
        ]
        shape_name = (
            f"{control_shape.value}Shape" if index == 0 else f"{control_shape.value}Shape{index}"
        )
        child_curve_transform: str = cmds.curve(
            pointWeight=position_weights, knot=knots, periodic=periodic, degree=degree
        )
        curve_shape_node: str = get_shapes(child_curve_transform)[0]
        cmds.parent(curve_shape_node, curve_transform, shape=True, relative=True)
        curve_shape_node = cmds.rename(curve_shape_node, shape_name)
        cmds.delete(child_curve_transform)
    if parent is not None:
        cmds.parent(curve_transform, parent)
    if name is not None:
        curve_transform = cmds.rename(curve_transform, name)
    return curve_transform
