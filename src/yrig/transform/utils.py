import maya.cmds as cmds
from maya.api.OpenMaya import (
    MAngle,
    MDagPath,
    MEulerRotation,
    MFnDagNode,
    MMatrix,
    MPoint,
    MSelectionList,
)

from yrig.transform.matrix import (
    get_world_matrix,
    set_local_matrix,
    set_world_matrix,
)


def partial_path_name(transform: str) -> str:
    """Returns the minimum path string necessary to uniquely identify the object."""
    sel = MSelectionList()
    sel.add(transform)
    dag_path: MDagPath = sel.getDagPath(0)
    mfn_dag = MFnDagNode(dag_path)
    return mfn_dag.partialPathName()


def create_transform(
    name: str,
    parent: str | None = None,
    transform: str | MMatrix | None = None,
) -> str:
    """Create an transform node with optional parent and initial transform.

    Args:
        name: Name of the new node.
        parent: Optional parent transform.
        transform: ``None``, a transform name to match, or a world space ``MMatrix`` to apply.

    Returns:
        The created transform name.
    """
    created_transform: str
    if parent:
        created_transform = cmds.group(empty=True, name=name, parent=parent)
    else:
        created_transform = cmds.group(empty=True, name=name, world=True)
    if transform is None:
        pass
    elif isinstance(transform, str):
        match_transform(created_transform, transform)
    elif isinstance(transform, MMatrix):
        set_world_matrix(created_transform, transform, use_joint_orient=True)
    else:
        raise RuntimeError(f"{transform} is not a valid transform name or MMatrix")
    return created_transform


def get_shapes(transform: str) -> list[str]:
    """Return the non-intermediate shape nodes parented under a transform.

    Queries the DAG hierarchy for shape children of *transform*, filtering
    out intermediate (construction-history) shapes so that only the
    renderable/visible shapes are returned.

    Args:
        transform: The name of the DAG transform node to inspect.

    Returns:
        A list of shape node names directly under the transform.

    Raises:
        RuntimeError: If *transform* has no child shape nodes.
    """
    # list the shapes of node
    shape_list: list[str] = cmds.listRelatives(
        transform, shapes=True, noIntermediate=True, children=True
    )

    if shape_list:
        return shape_list
    else:
        raise RuntimeError(f"{transform} has no child shape nodes")


def get_shape(object: str) -> str | None:
    """
    Return the first non-intermediate shape node associated with a DAG object.

    If the input is a transform, its child shapes are queried and the first
    valid (non-intermediate) shape is returned. If the input is already a
    shape node, it is returned directly. If no valid shape is found, ``None``
    is returned.

    Args:
        object: Name of a Maya DAG node (transform or shape).

    Returns:
        The name of the associated shape node, or ``None`` if no shape exists.
    """
    shape: str
    if cmds.nodeType(object) == "transform":
        shape_list: list[str] = cmds.listRelatives(
            object, shapes=True, noIntermediate=True, children=True
        )
        if shape_list:
            shape = shape_list[0]
            return shape
        else:
            return None

    if cmds.objectType(object, isAType="shape"):
        shape = object
        return shape
    else:
        return None


def bake_shape(transform: str, zero_pivot: bool = True) -> None:
    cmds.makeIdentity(transform, apply=True)
    if zero_pivot:
        cmds.xform(transform, pivots=(0, 0, 0))


def get_position(transform: str, world_space: bool = True) -> MPoint:
    """Return the translation of a transform as an ``MPoint``.

    Args:
        transform: The name of the Maya transform node to query.
        world_space: If ``True`` (the default), the position is returned in
            world space.  If ``False``, local (object) space is used.

    Returns:
        An ``MPoint`` containing the XYZ translation of the transform.
    """
    return MPoint(cmds.xform(transform, query=True, worldSpace=world_space, translation=True))


def match_transform(transform: str, target_transform: str, use_joint_orient: bool = True) -> None:
    """
    Match a transform to another in world space.

    Args:
        transform: Object to be moved to the specified transform.
        target_transform: Name of the transform to match to.
        use_joint_orient: When ``True``, if the transform is a joint the rotation will be zeroed and applied to the jointOrient.
    """
    source_matrix: MMatrix = get_world_matrix(transform=target_transform)
    set_world_matrix(transform=transform, matrix=source_matrix)


def match_location(transform: str, target_transform: str) -> None:
    """
    Match a transforms location to another in world space.

    Args:
        transform: Object to be moved to the specified transform.
        target_transform: Name of the transform to match to.
    """
    # Get the world-space translation of the target object.
    target_pos: tuple[float, float, float] = cmds.xform(  # type: ignore
        target_transform, query=True, worldSpace=True, translation=True
    )

    # Set the world-space translation of the source object to the target's position.
    cmds.xform(transform, worldSpace=True, translation=target_pos)


def zero_transform(transform: str, local: bool = True) -> None:
    """Reset a transform's matrix to identity, effectively zeroing it out.

    Sets translation, rotation, scale, and shear back to their default
    values.  When *local* is ``True`` the local matrix is zeroed (the node
    stays parented and the parent's world matrix is preserved).  When
    ``False`` the world matrix is set to identity, moving the node to the
    world origin.

    Args:
        transform: The name of the Maya transform node to zero.
        local: If ``True`` (the default), zero the local matrix.  If
            ``False``, zero the world matrix.
    """
    if local:
        set_local_matrix(transform, MMatrix.kIdentity)
    else:
        set_world_matrix(transform, MMatrix.kIdentity)


def zero_rotate_axis(transform: str) -> None:
    """Zero out the ``rotateAxis`` attribute while preserving the world-space orientation.

    For **joints**, Maya's ``zeroScaleOrient`` command is used.  For regular
    transforms the rotateAxis is set to ``(0, 0, 0)`` and the world-space
    orientation is restored via a temporary helper node so the visual
    position in the viewport does not change.

    Args:
        transform: The name of the Maya transform or joint node to modify.
    """
    node_type = cmds.nodeType(transform)
    if node_type == "joint":
        cmds.joint(transform, edit=True, zeroScaleOrient=True)
    else:
        temp_transform = create_transform(name=f"{transform}_temp")
        match_transform(temp_transform, transform)
        cmds.setAttr(f"{transform}.rotateAxis", 0, 0, 0, type="float3")  # type: ignore
        match_transform(transform, temp_transform)
        cmds.delete(temp_transform)


def clean_parent(transform: str, parent: str, joint_orient: bool = True) -> None:
    """
    Parent a node while preserving its world transform without creating
    Maya's intermediate "compensation" transforms.

    - For transforms: world matrix is preserved.
    - For joints (if joint_orient=True): rotation is baked into jointOrient
      and rotate is zeroed, keeping the joint clean for IK/FK.

    Args:
        transform: Node to reparent.
        parent: New parent node.
        joint_orient: If True, bake rotation into jointOrient for joints.
    """
    object_world_matrix: MMatrix = get_world_matrix(transform)
    cmds.parent(transform, parent, relative=True)
    set_world_matrix(transform, object_world_matrix, use_joint_orient=joint_orient)
