from typing import Sequence

import maya.cmds as cmds

from yrig.maya_api.node import ConditionNode


def create_parent_space_switch(
    target_transform: str,
    parent_list: Sequence[str],
    target_control: str,
    attribute_name: str = "space",
) -> str:
    """Create a parent space switch setup.

    Args:
        target_transform: Transform that receives the parent constraint.
        parent_list: List of parent spaces.
        target_control: Control that receives the enum attribute.
        attribute_name: Name of the enum attribute.

    Returns:
        The created parentConstraint node.
    """

    # ------------------------------------------------------------------
    # Validate inputs
    # ------------------------------------------------------------------

    if not cmds.objExists(target_transform):
        raise RuntimeError(f"Target transform does not exist: {target_transform}")

    if not cmds.objExists(target_control):
        raise RuntimeError(f"Target control does not exist: {target_control}")

    if not parent_list:
        raise RuntimeError("Parent list is empty.")

    for parent in parent_list:
        if not cmds.objExists(parent):
            raise RuntimeError(f"Parent does not exist: {parent}")

    # ------------------------------------------------------------------
    # Add enum attribute
    # ------------------------------------------------------------------

    enum_names = ":".join(parent_list)

    attr_path = f"{target_control}.{attribute_name}"

    if not cmds.attributeQuery(attribute_name, node=target_control, exists=True):
        cmds.addAttr(
            target_control,
            longName=attribute_name,
            attributeType="enum",
            enumName=enum_names,
            keyable=True,
        )

    # ------------------------------------------------------------------
    # Create parent constraint
    # ------------------------------------------------------------------

    parent_constraint: str = cmds.parentConstraint(  # type:ignore
        parent_list,  # type:ignore
        target_transform,
        maintainOffset=True,
        name=f"{target_transform}_spaceSwitch_PC",
    )[0]

    # ------------------------------------------------------------------
    # Create condition nodes
    # ------------------------------------------------------------------

    weight_aliases = cmds.parentConstraint(parent_constraint, query=True, weightAliasList=True)

    for index, (parent, weight_attr) in enumerate(zip(parent_list, weight_aliases)):  # type:ignore
        condition = ConditionNode(name=f"{target_transform}_{parent}_spaceSwitch_COND")

        # Equal operation
        # 0 == Equal in Maya condition node

        condition.operation.set(0)

        # Compare enum value
        condition.first_term.connect_from(attr_path)

        condition.second_term.set(index)
        # True = 1
        condition.color_if_true.r.set(1)

        # False = 0
        condition.color_if_false.r.set(0)

        # Drive parentConstraint weight
        condition.out_color.r.connect_to(f"{parent_constraint}.{weight_attr}")

    return parent_constraint
