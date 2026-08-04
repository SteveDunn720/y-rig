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

    geometry = cast(
        list[str] | None,
        cmds.blendShape(blendshape_node, query=True, geometry=True),
    )

    if isinstance(geometry, list):
        meshes.extend(geometry)

    return BlendShape(node=blendshape_node, targets=targets, meshes=meshes)


def create_blendshape(
    target_mesh: str,
    blendshape_name: str,
    front_of_chain: bool = True,
) -> BlendShape:
    """Create an empty blendShape and return its data."""
    if cmds.objExists(blendshape_name):
        if cmds.nodeType(blendshape_name) != "blendShape":
            raise TypeError(f"{blendshape_name} exists but is not a blendShape node")

        return get_blendshape_data(blendshape_name)

    result = cast(
        list[str],
        cmds.blendShape(
            target_mesh,
            name=blendshape_name,
            frontOfChain=front_of_chain,
        ),
    )

    if not result:
        raise RuntimeError(f"Failed to create blendShape: {blendshape_name}")

    return get_blendshape_data(result[0])


def find_blendshape(mesh: str) -> BlendShape:
    """Find the first blendShape in a mesh's history."""
    history = (
        cmds.listHistory(
            mesh,
            pruneDagObjects=True,
        )
        or []
    )

    blendshape_nodes = (
        cmds.ls(
            history,  # type:ignore
            type="blendShape",
        )
        or []
    )

    if not blendshape_nodes:
        raise ValueError(f"No blendShape was found on {mesh}")

    if len(blendshape_nodes) > 1:
        cmds.warning(f"Multiple blendShapes found on {mesh}. Using {blendshape_nodes[0]}")

    return get_blendshape_data(blendshape_nodes[0])


def build_blendshape_networks(
    blendshape: BlendShape, targets: list[ShapeTarget] | None = None
) -> dict[str, str]:
    """
    Creates one network node per blendshape type and connects
    custom attributes to the corresponding blendshape targets.

    Example:
        mouth_l_up_07
            -> mouth_l_nw.up_07

        mouth_l_up_07_out_10
            -> mouth_l_nw.up_07_out_10
    """
    network_nodes: dict[str, str] = {}

    if targets:
        pass
        # only connects targets in the list if htere arent any then we just do all of them
    else:
        for shape in blendshape.targets:
            parts = shape.name.split("_")

            if len(parts) < 3:
                cmds.warning(f"Invalid blendshape name: {shape.name}")
                continue

            target_type = "_".join(parts[:2])
            target_name = "_".join(parts[2:])

            network_name = f"{target_type}_nw"

            if target_type not in network_nodes:
                if cmds.objExists(network_name):
                    network_node = network_name
                else:
                    network_node = cmds.createNode(
                        "network",
                        name=network_name,
                    )

                network_nodes[target_type] = network_node

            network_node = network_nodes[target_type]

            if not cmds.attributeQuery(
                target_name,
                node=network_node,
                exists=True,
            ):
                cmds.addAttr(
                    network_node,
                    longName=target_name,
                    attributeType="double",
                    defaultValue=0.0,
                    minValue=0.0,
                    maxValue=1.0,
                    keyable=True,
                )

            cmds.connectAttr(
                f"{network_node}.{target_name}",
                shape.attr,
                force=True,
            )

    return network_nodes
