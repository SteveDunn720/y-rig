import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import maya.cmds as cmds


@dataclass
class ShapeTarget:
    name: str
    index: int
    attr: str


@dataclass
class BlendShape:
    node: str
    targets: list[ShapeTarget]
    meshes: list[str]

    def get_target(self, target: str | int) -> ShapeTarget:
        for shape in self.targets:
            if shape.name == target:
                return shape

            if shape.index == target:
                return shape

        raise ValueError(f"{target} does not exist")


def import_blendshape(
    target_mesh: str,
    shape_path: Path,
    blendshape_name: str,
) -> BlendShape:
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
        The blendShape as a blendshape data class.
    """

    if not os.path.exists(shape_path):
        raise FileNotFoundError(f"Shape file does not exist: {shape_path}")

    # Reuse existing blendShape if it already exists
    if cmds.objExists(blendshape_name):
        blendshape_node = blendshape_name

    else:
        result = cast(
            list[str],
            cmds.blendShape(
                target_mesh,
                name=blendshape_name,
                frontOfChain=True,
            ),
        )

        if not result:
            raise RuntimeError(f"Failed to create blendShape: {blendshape_name}")

        blendshape_node = result[0]

    # Import shape data
    cmds.blendShape(
        blendshape_node,
        edit=True,
        ip=str(shape_path),
    )

    return get_blendshape_data(blendshape_node)


def export_blendshape(
    blendshape_node: str,
    shape_path: Path,
) -> Path:
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
        export=str(shape_path),
    )

    return shape_path


def get_blendshape_data(blendshape_node: str) -> BlendShape:
    targets = []

    # Get target aliases
    aliases = cmds.aliasAttr(blendshape_node, query=True) or []

    for i in range(0, len(aliases), 2):
        attr_name = aliases[i]
        attr_path = aliases[i + 1]

        # Extract weight index
        index = int(attr_path.split("[")[-1].replace("]", ""))

        targets.append(
            ShapeTarget(name=attr_name, index=index, attr=f"{blendshape_node}.{attr_name}")
        )

    # Find connected meshes
    meshes = []

    geometry = cmds.blendShape(blendshape_node, query=True, geometry=True) or []

    if isinstance(geometry, list):
        meshes.extend(geometry)

    return BlendShape(node=blendshape_node, targets=targets, meshes=meshes)
