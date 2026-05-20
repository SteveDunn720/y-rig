import maya.cmds as cmds

import os


def read_blendshape(
    target_mesh: str,
    shape_path: str,
    blendshape_name: str,
) -> str:
    """
    Create and load a blendShape from a .shape/.shp file.

    Args:
        target_mesh:
            Mesh the blendShape will deform.

        shape_path:
            Path to the exported shape file.

        blendshape_name:
            Name of the blendShape node.

    Returns:
        The blendShape node name.
    """

    if not os.path.exists(shape_path):
        raise FileNotFoundError(f"Shape file does not exist: {shape_path}")

    # Reuse existing blendShape if it already exists
    if cmds.objExists(blendshape_name):
        blendshape_node = blendshape_name

    else:
        result: list[str] = cmds.blendShape(  # type:ignore
            target_mesh,
            name=blendshape_name,
            frontOfChain=True,
        )

        if not result:
            raise RuntimeError(f"Failed to create blendShape: {blendshape_name}")

        blendshape_node = result[0]

    # Import shape data
    cmds.blendShape(
        blendshape_node,
        edit=True,
        ip=shape_path,
    )

    return blendshape_node


def write_blendshape(
    blendshape_node: str,
    shape_path: str,
) -> str:
    """
    Export a blendShape node to a .shape/.shp file.

    Args:
        blendshape_node:
            Name of the blendShape node.

        shape_path:
            Output file path.

    Returns:
        The exported file path.
    """

    if not cmds.objExists(blendshape_node):
        raise RuntimeError(f"BlendShape does not exist: {blendshape_node}")

    if cmds.nodeType(blendshape_node) != "blendShape":
        raise TypeError(f"{blendshape_node} is not a blendShape node")

    # Ensure output directory exists
    directory = os.path.dirname(shape_path)

    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    # Export shape file
    cmds.blendShape(
        blendshape_node,
        edit=True,
        export=shape_path,
    )

    return shape_path
