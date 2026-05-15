from typing import Callable, Sequence

from maya import cmds
from maya.api.OpenMaya import MDagPath, MFnNurbsCurve, MPoint, MSelectionList, MSpace

from yrig.maya_api.enum import Axis
from yrig.maya_api.node import MotionPathNode
from yrig.spline import generate_knots
from yrig.spline.math import create_periodic_cv_list
from yrig.transform import create_transform, get_shape, get_shapes, matrix_constraint
from yrig.transform.utils import set_position


def bound_curve_from_transforms(
    transforms: Sequence[str],
    name: str,
    parent: str | None = None,
    degree: int = 3,
    knots: Sequence[float] | None = None,
    periodic: bool = False,
    create_pins: bool = True,
    hide: bool = False,
) -> str:
    """
    Create a NURBS curve whose CVs are driven by the given transforms.

    CV control points are connected to each transform's ``.translate`` so the
    curve follows them in real time. When *create_pins* is True, intermediate
    pin nodes are created under a ``{curve_name}_grp`` group and
    translation-constrained to the source transforms; otherwise the CVs connect
    to the source transforms directly.

    Args:
        transforms: Ordered transform names, one per CV.
        name: Name for the created curve transform.
        parent: Optional parent for the curve and its pin group.
        degree: Curve degree (default ``3``, cubic).
        knots: Custom knot vector. Auto-generated when ``None``. First and last
            values are stripped before passing to Maya.
        periodic: Create a closed loop by wrapping the first *degree* CVs.
        create_pins: Create intermediate pin transforms instead of connecting
            CVs to the source transforms directly.

    Returns:
        The name of the created curve transform node.
    """
    curve_transform_name = name
    curve_group: str | None
    if create_pins:
        curve_group = create_transform(name=f"{curve_transform_name}_grp", parent=parent)
    else:
        curve_group = None

    full_knots = (
        knots
        if knots is not None
        else generate_knots(len(transforms), degree=degree, periodic=periodic)
    )
    maya_knots: Sequence[float] = full_knots[1:-1]
    extended_cvs = create_periodic_cv_list(transforms, degree) if periodic else transforms
    curve_transform: str = cmds.curve(
        name=curve_transform_name,
        point=[  # type: ignore
            cmds.xform(cv, query=True, worldSpace=True, translation=True) for cv in extended_cvs
        ],
        periodic=periodic,
        knot=list(maya_knots),
        degree=degree,
    )
    curve_shape = get_shapes(curve_transform)[0]
    cmds.rename(curve_shape, f"{curve_transform_name}Shape")

    if curve_group is not None:
        cmds.parent(curve_transform, curve_group, relative=True)

    if hide:
        if curve_group is not None:
            cmds.hide(curve_group)
        else:
            cmds.hide(curve_transform)

    extended_cv_mapping: dict[str, str] = {}
    if create_pins:
        for index, transform in enumerate(transforms):
            cv = create_transform(name=f"{curve_transform}_cv{index}", parent=curve_group)
            matrix_constraint(
                transform, cv, rotate=False, scale=False, shear=False, keep_offset=False
            )
            if transform not in extended_cv_mapping:
                extended_cv_mapping[transform] = cv
    else:
        extended_cv_mapping = {transform: transform for transform in extended_cvs}

    for index, transform in enumerate(extended_cvs):
        cmds.connectAttr(
            f"{extended_cv_mapping[transform]}.translate",
            f"{curve_transform}.controlPoints[{index}]",
        )
    return curve_transform


def get_curve_cvs(curve: str, world_space: bool = True) -> list[MPoint]:
    """
    Get all CV positions from a NURBS curve.

    Args:
        curve: Curve transform or nurbsCurve shape node.
        world_space: Whether to return CV positions in world space.
            If ``False``, positions are returned in object space.

    Returns:
        List of CV positions as ``MPoint`` objects.
    """
    shape = get_shape(curve)
    if shape is None:
        raise RuntimeError(f"{curve} had no shape node!")
    if not cmds.nodeType(shape) == "nurbsCurve":
        raise RuntimeError(f"{curve} is not a nurbsCurve")

    sel = MSelectionList()
    sel.add(shape)
    dag_path: MDagPath = sel.getDagPath(0)
    curve_fn = MFnNurbsCurve(dag_path)
    return curve_fn.cvPositions(MSpace.kWorld if world_space else MSpace.kObject)


def create_transforms_at_curve_cvs(
    curve: str, name_format: str | Callable[[int], str], parent: str | None = None
) -> list[str]:
    """
    Create transforms positioned at each CV of a NURBS curve.

    Args:
        curve: Curve transform or nurbsCurve shape node.
        name_format: Naming rule for created transforms.
            If a string is provided, names are generated as "{name_format}_{index}".
            If a callable is provided, it is called with the CV index and must return the transform name.
        parent: Optional parent transform for created nodes.

    Returns:
        List of created transform node names.
    """
    curve_cvs = get_curve_cvs(curve)
    transforms: list[str] = []
    for index, cv in enumerate(curve_cvs):
        transform_name: str
        if isinstance(name_format, str):
            transform_name = f"{name_format}_{index}"
        else:
            transform_name = name_format(index)
        transform = create_transform(transform_name, parent)
        set_position(transform, cv)
        transforms.append(transform)
    return transforms


def pin_to_curve_with_motion_path(
    curve: str,
    pinned_transform: str,
    parameter: float,
    arc_length: bool = True,
    orient: bool = True,
    front_axis: Axis = Axis.X,
    up_axis: Axis = Axis.Z,
    up_vector: tuple[float, float, float] = (0, 0, 1),
) -> MotionPathNode:
    curve_shape = get_shape(curve)
    if curve_shape is None:
        raise RuntimeError(f"{curve} had no curve shape")
    motion_path = MotionPathNode(f"{pinned_transform}_motion_path")
    motion_path.geometry_path.connect_from(f"{curve_shape}.local")
    motion_path.u_value.set(parameter)
    motion_path.fraction_mode.set(arc_length)
    motion_path.follow.set(orient)
    if orient:
        motion_path.rotate.connect_to(f"{pinned_transform}.rotate")
        motion_path.rotate_order.connect_from(f"{pinned_transform}.rotateOrder")
        motion_path.front_axis.set(front_axis)
        motion_path.up_axis.set(up_axis)
        motion_path.world_up_vector.set(up_vector)
    motion_path.all_coordinates.connect_to(f"{pinned_transform}.translate")

    return motion_path
