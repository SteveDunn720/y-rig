from maya import cmds
from maya.api.OpenMaya import MMatrix

from yrig.maya_api.attribute import MatrixAttribute
from yrig.maya_api.enum import AimMatrixAxisMode
from yrig.maya_api.node import AimMatrixNode, MultiplyVectorByMatrixNode
from yrig.name import get_short_name
from yrig.transform.matrix import (
    drive_transform_with_matrix,
    get_parent_inverse_matrix,
    get_world_matrix,
    multiply_matrices,
)


def matrix_constraint(
    source_transform: str,
    constrain_transform: str,
    keep_offset: bool = True,
    local_space: bool = True,
    use_joint_orient: bool = False,
    translate: bool = True,
    rotate: bool = True,
    scale: bool = True,
    shear: bool = True,
) -> None:
    """
    Constrain a transform to follow another in world space using a pure-matrix node graph.

    Args:
        source_transform: Transform to match (the driver).
        constrain_transform: Transform to constrain (the driven).
        keep_offset: keep the offset of the constrained transform to the source at time of constraint generation.
        local_space: if False the constrained transform will have inheritsTransform turned off.
        use_joint_orient: when true the joint orient is taken into account, otherwise it is set to zero.
        translate: whether to constrain translation.
        rotate: whether to constrain rotation.
        scale: whether to constrain scale.
        shear: whether to constrain shear.
    """
    constraint_name: str = get_short_name(constrain_transform)

    matrices: list[MatrixAttribute | MMatrix] = []

    if keep_offset:
        # Get the offset matrix
        offset_matrix: MMatrix = (
            get_world_matrix(constrain_transform) * get_world_matrix(source_transform).inverse()
        )
        matrices.append(offset_matrix)

    matrices.append(MatrixAttribute(f"{source_transform}.worldMatrix[0]"))
    if local_space:
        matrices.append(MatrixAttribute(f"{constrain_transform}.parentInverseMatrix[0]"))
    else:
        cmds.setAttr(f"{constrain_transform}.inheritsTransform", 0)  # type: ignore

    mult_matrix = multiply_matrices(f"{constraint_name}_ConstraintMatrixMult", matrices=matrices)
    drive_transform_with_matrix(
        mult_matrix.matrix_sum,
        transform=constrain_transform,
        translate=translate,
        rotate=rotate,
        scale=scale,
        shear=shear,
        use_joint_orient=use_joint_orient,
    )


def local_constraint(
    source_transform: str,
    constrain_transform: str,
    reference_space: str,
    keep_offset: bool = True,
    use_joint_orient: bool = False,
    translate: bool = True,
    rotate: bool = True,
    scale: bool = True,
    shear: bool = True,
) -> None:
    """
    Constrain a transform to follow another relative to a reference space.

    The driven transform follows the source transform's motion *within the
    coordinate system of the reference space*, while preserving its existing
    placement relative to its own parent hierarchy.

    This is useful when a control should inherit motion from another object
    without being fully parented beneath it. For example, mouth controls can
    follow jaw motion relative to the head while still allowing independent
    local movement from their own control hierarchy.

    Args:
        source_transform: Transform to match (the driver).
        constrain_transform: Transform to constrain (the driven).
        keep_offset: keep the offset of the constrained transform to the source at time of constraint generation.
        local_space: if False the constrained transform will have inheritsTransform turned off.
        use_joint_orient: when true the joint orient is taken into account, otherwise it is set to zero.
        translate: whether to constrain translation.
        rotate: whether to constrain rotation.
        scale: whether to constrain scale.
        shear: whether to constrain shear.
    """
    constraint_name: str = get_short_name(constrain_transform)

    matrices: list[MatrixAttribute | MMatrix] = []

    if keep_offset:
        offset_matrix = (
            get_world_matrix(constrain_transform) * get_world_matrix(source_transform).inverse()
        )
        matrices.append(offset_matrix)

    matrices.append(MatrixAttribute(f"{source_transform}.worldMatrix[0]"))
    matrices.append(MatrixAttribute(f"{reference_space}.worldInverseMatrix[0]"))

    reference_offset_matrix = get_world_matrix(reference_space) * get_parent_inverse_matrix(
        constrain_transform
    )
    matrices.append(reference_offset_matrix)

    mult_matrix = multiply_matrices(f"{constraint_name}_ConstraintMatrixMult", matrices=matrices)
    drive_transform_with_matrix(
        mult_matrix.matrix_sum,
        transform=constrain_transform,
        translate=translate,
        rotate=rotate,
        scale=scale,
        shear=shear,
        use_joint_orient=use_joint_orient,
    )


def matrix_normal_orient_constraint(
    matrix: MatrixAttribute,
    twist_transform: str,
    driven_transform: str,
    normal_axis: tuple[float, float, float] = (0, 0, 1),
    secondary_axis: tuple[float, float, float] = (1, 0, 0),
) -> AimMatrixNode:
    """
    Orients a matrix so that one axis is locked to a fixed normal direction while
    the secondary axis tracks the orientation of a twist transform.

    Args:
        matrix: The world-space input matrix to be reoriented.
        twist_transform: Name of the Maya transform whose axial orientation
            drives the secondary (tangent) axis of matrix.
        driven_transform: Name of the Maya transform that owns the resulting
            orientation.  Its ``parentInverseMatrix`` is used to localize the
            computation, and it acts as the reference space for the aim node's
            post-space.
        normal_axis: The axis, expressed in local space, that should remain
            fixed and un-twisted.
        secondary_axis: The axis, expressed in local space, used as the
            up/tangent reference for the aim calculation.  Also defines which
            axis of ``twist_transform`` is projected into local space.

    Returns:
        A ``AimMatrixNode`` which calculates the twist-corrected local matrix.
    """
    matrix_localize = multiply_matrices(
        f"{driven_transform}_matrix_localize",
        matrices=(
            matrix,
            MatrixAttribute(f"{driven_transform}.parentInverseMatrix[0]"),
        ),
    )
    twist_localize = multiply_matrices(
        f"{driven_transform}_twist_localize",
        matrices=(
            MatrixAttribute(f"{twist_transform}.worldMatrix[0]"),
            MatrixAttribute(f"{driven_transform}.parentInverseMatrix[0]"),
        ),
    )

    normal_vector = MultiplyVectorByMatrixNode.create(f"{twist_transform}_local_normal")
    normal_vector.input_matrix.connect_from(matrix_localize.matrix_sum)
    normal_vector.input_vector.set(normal_axis)

    secondary_vector = MultiplyVectorByMatrixNode.create(f"{twist_transform}_local_secondary")
    secondary_vector.input_matrix.connect_from(twist_localize.matrix_sum)
    secondary_vector.input_vector.set(secondary_axis)

    aim_matrix_node = AimMatrixNode.create(f"{driven_transform}_twist")
    aim_matrix_node.primary.input_axis.set(normal_axis)
    aim_matrix_node.primary.target_vector.connect_from(normal_vector.output)
    aim_matrix_node.primary.mode.set(AimMatrixAxisMode.ALIGN)
    aim_matrix_node.secondary.input_axis.set(secondary_axis)
    aim_matrix_node.secondary.target_vector.connect_from(secondary_vector.output)
    aim_matrix_node.secondary.mode.set(AimMatrixAxisMode.ALIGN)

    drive_transform_with_matrix(
        aim_matrix_node.output_matrix,
        driven_transform,
        translate=False,
        scale=False,
        shear=False,
    )

    return aim_matrix_node
