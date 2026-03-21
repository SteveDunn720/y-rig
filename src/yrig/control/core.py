from maya import cmds
from maya.api.OpenMaya import MMatrix

from yrig.build.mgear_api.control import add_ctl
from yrig.control.curve import create_curve
from yrig.control.serialize import ControlShape
from yrig.name import MIDDLE_SIDE_NAME, get_side
from yrig.transform.matrix import get_world_matrix
from yrig.transform.structs import RotationOrder


def create_control(
    name: str,
    parent: str | None,
    transform: str | MMatrix | None = None,
    control_shape: ControlShape | str = ControlShape.CIRCLE,
    rotation_order: RotationOrder = RotationOrder.XYZ,
    limit_min_scale: bool = True,
):
    transform_matrix: MMatrix
    if transform is not None:
        if isinstance(transform, str):
            transform_matrix = get_world_matrix(transform)
        elif isinstance(transform, MMatrix):
            transform_matrix = transform
        else:
            raise RuntimeError(f"{transform} is not a valid transform name or MMatrix")
    else:
        transform_matrix = MMatrix.kIdentity
    # We call a function to create an mGear compatible control here, since mGear is rather specific about what it needs.
    # Feel free to replace this if you ditch mGear.
    control_transform = str(
        add_ctl(
            name,
            parent,
            transform_matrix,
            side=get_side(name) or MIDDLE_SIDE_NAME,
            control_icon_creator=lambda: create_curve(name, control_shape, parent),
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
