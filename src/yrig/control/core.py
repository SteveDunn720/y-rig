from maya import cmds
from maya.api.OpenMaya import MMatrix

from yrig.control.curve import create_curve
from yrig.control.serialize import ControlShape
from yrig.structs.transform import RotationOrder
from yrig.transform import match_transform, set_world_matrix


def create_control(
    name: str,
    parent: str | None,
    transform: str | MMatrix | None = None,
    control_shape: ControlShape | str = ControlShape.CIRCLE,
    rotation_order: RotationOrder = RotationOrder.XYZ,
    limit_min_scale: bool = True,
):
    control_transform = create_curve(name, control_shape, parent)
    if transform is not None:
        if isinstance(transform, str):
            match_transform(control_transform, transform)
        elif isinstance(transform, MMatrix):
            set_world_matrix(control_transform, transform)
        else:
            raise RuntimeError(f"{transform} is not a valid transform name or MMatrix")

    cmds.setAttr(f"{control_transform}.rotateOrder", rotation_order.value)
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
