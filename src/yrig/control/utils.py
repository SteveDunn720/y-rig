from maya import cmds

from yrig.name import get_side


def get_tagged_controls(side: str | None = None) -> list[str]:
    """
    Returns all transform nodes tagged as controllers via a connected controller node.

    Returns:
        list: A list of transform node names that are tagged as controllers.
    """
    controller_nodes: list[str] = cmds.ls(type="controller")
    tagged_controls: list[str] = []
    for control_node in controller_nodes:
        connected: list[str] = cmds.listConnections(
            f"{control_node}.controllerObject", source=True, destination=False
        )
        control = connected[0]
        if side:
            if get_side(control_node) == side:
                tagged_controls.append(control)
        elif connected:
            tagged_controls.append(control)

    return tagged_controls
