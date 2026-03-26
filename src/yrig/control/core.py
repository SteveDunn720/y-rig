from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from maya import cmds
from maya.api.OpenMaya import MMatrix

from yrig.build.mgear_api.control import add_ctl
from yrig.control.serialize import ControlShape, create_curve
from yrig.name import MIDDLE_SIDE_NAME, get_side
from yrig.transform import create_transform
from yrig.transform.matrix import get_world_matrix
from yrig.transform.structs import Direction, RotationOrder
from yrig.transform.utils import bake_shape

CONTROL_SUFFIX = "_ctl"
OFFSET_SUFFIX = "_npo"

_control_collection_stack: list[list[Control]] = []


def _register_control(ctrl: "Control") -> None:
    if _control_collection_stack:
        _control_collection_stack[-1].append(ctrl)


@contextmanager
def collect_controls() -> Iterator[list[Control]]:
    # Create a bucket to collect the controls created in the with block
    # then put it on the stack so that _register_control will add to this bucket
    bucket: list[Control] = []
    _control_collection_stack.append(bucket)
    try:
        yield bucket
    finally:
        _control_collection_stack.pop()


@dataclass
class Control:
    control_transform: str
    offset_transform: str | None = None


def _create_control_curve(
    name: str,
    control_shape: ControlShape | str = ControlShape.CIRCLE,
    direction: Direction = "y",
    size: float = 1,
    dimensions: tuple[float, float, float] = (1, 1, 1),
) -> str:
    curve_transform = create_curve(name, control_shape)
    bake: bool = False
    match direction:
        case "y":
            pass
        case "-y":
            cmds.rotate(180, 0, 0, curve_transform)
            bake = True
        case "x":
            cmds.rotate(0, 0, -90, curve_transform)
            bake = True
        case "-x":
            cmds.rotate(0, 0, 90, curve_transform)
            bake = True
        case "z":
            cmds.rotate(90, 0, 0, curve_transform)
            bake = True
        case "-z":
            cmds.rotate(-90, 0, 0, curve_transform)
            bake = True
        case _:
            raise RuntimeError(
                f"{direction} is not a valid direction. It should be x,y,z or -x,-y,-z."
            )

    if (size != 1) or (dimensions != (1, 1, 1)):
        scaled_dimensions = (size * dimension for dimension in dimensions)
        cmds.scale(*scaled_dimensions, curve_transform, relative=False)  # type: ignore
        bake = True

    if bake:
        bake_shape(transform=curve_transform)
    return curve_transform


def create_control(
    name: str,
    parent: str | None,
    transform: str | MMatrix | None = None,
    control_shape: ControlShape | str = ControlShape.CIRCLE,
    create_offset: bool = True,
    direction: Direction = "y",
    size: float = 1,
    dimensions: tuple[float, float, float] = (1, 1, 1),
    rotation_order: RotationOrder = RotationOrder.XYZ,
    limit_min_scale: bool = True,
):
    transform_matrix: MMatrix | None
    if transform is not None:
        if isinstance(transform, str):
            transform_matrix = get_world_matrix(transform)
        elif isinstance(transform, MMatrix):
            transform_matrix = transform
        else:
            raise RuntimeError(f"{transform} is not a valid transform name or MMatrix")
    else:
        transform_matrix = None

    offset_transform: str | None = None
    if create_offset:
        offset_transform = create_transform(
            name=f"{name}{OFFSET_SUFFIX}", parent=parent, transform=transform_matrix
        )

    control_parent = parent if offset_transform is None else offset_transform
    control_name = f"{name}{CONTROL_SUFFIX}"
    # We call a function to create an mGear compatible control here, since mGear is rather specific about what it needs.
    # Feel free to replace this if you ditch mGear.
    control_transform = str(
        add_ctl(
            control_name,
            control_parent,
            transform_matrix if not create_offset else None,
            side=get_side(name) or MIDDLE_SIDE_NAME,
            control_icon_creator=lambda: _create_control_curve(
                control_name, control_shape, direction, size, dimensions
            ),
            rotation_order=str(rotation_order),
        )
    )

    if limit_min_scale:  # Comfort feature: make it so it's not possible to have negative scale
        min_scale: float = 0.01
        cmds.transformLimits(
            control_transform,
            enableScaleX=(True, False),
            scaleX=(min_scale, 1),
            enableScaleY=(True, False),
            scaleY=(min_scale, 1),
            enableScaleZ=(True, False),
            scaleZ=(min_scale, 1),
        )

    control = Control(control_transform=control_transform, offset_transform=offset_transform)
    _register_control(control)
    return control
