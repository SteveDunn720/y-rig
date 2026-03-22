from dataclasses import dataclass

from maya import cmds
from maya.api.OpenMaya import MMatrix

from yrig.build.mgear_api.control import add_ctl
from yrig.control.curve import create_curve
from yrig.control.serialize import ControlShape
from yrig.name import MIDDLE_SIDE_NAME, get_side
from yrig.transform.matrix import get_world_matrix
from yrig.transform.structs import RotationOrder
from yrig.transform.utils import bake_shape

CONTROL_SUFFIX = "_ctl"
OFFSET_SUFFIX = "_npo"


@dataclass
class Control:
    control_transform: str
    offset_transform: str | None = None


def _create_control_curve(
    name: str,
    control_shape: ControlShape | str = ControlShape.CIRCLE,
    size: float = 1,
    dimensions: tuple[float, float, float] = (1, 1, 1),
) -> str:
    curve_transform = create_curve(name, control_shape)
    if (size != 1) or (dimensions != (1, 1, 1)):
        scaled_dimensions = (size * dimension for dimension in dimensions)
        cmds.scale(*scaled_dimensions, curve_transform, relative=False)  # type: ignore
        bake_shape(transform=curve_transform)
    return curve_transform


def create_control(
    name: str,
    parent: str | None,
    transform: str | MMatrix | None = None,
    control_shape: ControlShape | str = ControlShape.CIRCLE,
    create_offset: bool = True,
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
        if parent is not None:
            offset_transform = cmds.group(empty=True, name=f"{name}{OFFSET_SUFFIX}", parent=parent)
        else:
            offset_transform = cmds.group(empty=True, name=f"{name}{OFFSET_SUFFIX}", world=True)

    control_parent = parent if offset_transform is None else offset_transform
    control_name = f"{name}{CONTROL_SUFFIX}"
    # We call a function to create an mGear compatible control here, since mGear is rather specific about what it needs.
    # Feel free to replace this if you ditch mGear.
    control_transform = str(
        add_ctl(
            control_name,
            control_parent,
            transform_matrix,
            side=get_side(name) or MIDDLE_SIDE_NAME,
            control_icon_creator=lambda: _create_control_curve(
                control_name, control_shape, size, dimensions
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

    return Control(control_transform=control_transform, offset_transform=offset_transform)
