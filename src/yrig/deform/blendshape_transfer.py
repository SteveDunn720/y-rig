from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field

import maya.cmds as cmds

from yrig.deform.proxy_wrap import (
    ProximityWrap,
    create_proximity_wrap,
)
from yrig.rbf.blendshape import (
    BlendShape,
    ShapeTarget,
    create_blendshape,
    find_blendshape,
    get_blendshape_data,
)


@dataclass
class TransferredShape:
    name: str
    source_index: int
    destination_index: int


@dataclass
class BlendShapeTransfer:
    source: BlendShape
    destination: BlendShape
    proximity_wrap: ProximityWrap | None
    transferred: list[TransferredShape] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def resolve_blendshape(
    blendshape_or_mesh: str | BlendShape,
) -> BlendShape:
    """Resolve a BlendShape from a dataclass, node, or mesh."""

    # Support BlendShape dataclasses even after module reloads.
    if hasattr(blendshape_or_mesh, "node"):
        node = blendshape_or_mesh.node

        if not isinstance(node, str):
            raise TypeError("BlendShape.node must be a string")

        if not cmds.objExists(node):
            raise ValueError(f"BlendShape node does not exist: {node}")

        if cmds.nodeType(node) != "blendShape":
            raise TypeError(f"{node} is not a blendShape node")

        return get_blendshape_data(node)

    if not isinstance(blendshape_or_mesh, str):
        raise TypeError("Expected a BlendShape dataclass, blendShape node, or mesh name")

    if not cmds.objExists(blendshape_or_mesh):
        raise ValueError(f"Object does not exist: {blendshape_or_mesh}")

    if cmds.nodeType(blendshape_or_mesh) == "blendShape":
        return get_blendshape_data(blendshape_or_mesh)

    return find_blendshape(blendshape_or_mesh)


def get_blendshape_mesh(blendshape: BlendShape) -> str:
    """Return the first mesh deformed by a BlendShape."""
    if not blendshape.meshes:
        raise ValueError(f"{blendshape.node} does not have any connected meshes")

    return blendshape.meshes[0]


def get_next_target_index(blendshape: BlendShape) -> int:
    """Return the next available target index."""
    if not blendshape.targets:
        return 0

    return max(target.index for target in blendshape.targets) + 1


def get_weight_values(
    blendshape: BlendShape,
) -> dict[int, float]:
    """Read all target weight values."""
    values: dict[int, float] = {}

    for target in blendshape.targets:
        values[target.index] = cmds.getAttr(f"{blendshape.node}.weight[{target.index}]")

    return values


def set_weight_values(
    blendshape: BlendShape,
    values: dict[int, float],
) -> None:
    """Set blendShape weight values by logical index."""
    for index, value in values.items():
        plug = f"{blendshape.node}.weight[{index}]"

        if not cmds.objExists(plug):
            continue

        if cmds.getAttr(plug, lock=True):
            raise RuntimeError(f"{plug} is locked")

        connections = (
            cmds.listConnections(
                plug,
                source=True,
                destination=False,
                plugs=True,
            )
            or []
        )

        if connections:
            raise RuntimeError(f"{plug} has an incoming connection from {connections[0]}")

        cmds.setAttr(plug, value)  # type:ignore


def zero_blendshape(blendshape: BlendShape) -> None:
    """Set all blendShape targets to zero."""
    set_weight_values(
        blendshape,
        {target.index: 0.0 for target in blendshape.targets},
    )


def add_blendshape_target(
    blendshape: BlendShape,
    base_mesh: str,
    target_mesh: str,
    target_name: str,
    index: int | None = None,
    target_weight: float = 1.0,
) -> BlendShape:
    """Add a mesh as a new target and return refreshed data."""
    if index is None:
        index = get_next_target_index(blendshape)

    cmds.blendShape(
        blendshape.node,
        edit=True,
        target=(
            base_mesh,
            index,
            target_mesh,
            target_weight,
        ),
        topologyCheck=True,
    )

    cmds.aliasAttr(
        target_name,
        f"{blendshape.node}.weight[{index}]",
    )

    return get_blendshape_data(blendshape.node)


def transfer_blendshapes(
    source_blendshape_or_mesh: str | BlendShape,
    target_mesh: str,
    target_blendshape: str | BlendShape | None = None,
    target_blendshape_name: str | None = None,
    target_names: list[str] | None = None,
    overwrite_existing: bool = False,
    delete_proximity_wrap: bool = True,
    falloff_scale: float | None = None,
    dropoff_rate_scale: float | None = None,
    smooth_influences: int | None = None,
    smooth_normals: int | None = None,
) -> BlendShapeTransfer:
    """Transfer blendShape targets between meshes using proximityWrap.

    Args:
        source_blendshape_or_mesh:
            Source BlendShape dataclass, blendShape node, or source mesh.

        target_mesh:
            Mesh that receives the transferred targets.

        target_blendshape:
            Existing target BlendShape dataclass or node.

        target_blendshape_name:
            Name used when creating a new target blendShape.

        target_names:
            Optional target names to transfer. Transfers all by default.

        overwrite_existing:
            Replace existing target deltas when names match.

        delete_proximity_wrap:
            Delete the temporary proximityWrap after transferring.

        falloff_scale:
            Optional proximity-wrap falloffScale setting.

        dropoff_rate_scale:
            Optional proximity-wrap dropoffRateScale setting.

        smooth_influences:
            Optional proximity-wrap smoothInfluences setting.

        smooth_normals:
            Optional proximity-wrap smoothNormals setting.

    Returns:
        BlendShapeTransfer containing the resulting data.
    """
    source = resolve_blendshape(source_blendshape_or_mesh)
    source_mesh = get_blendshape_mesh(source)

    if source_mesh == target_mesh:
        raise ValueError("Source mesh and target mesh must be different")

    if target_blendshape is None:
        if target_blendshape_name is None:
            short_name = target_mesh.split("|")[-1].split(":")[-1]
            target_blendshape_name = f"{short_name}_blendShape"

        destination = create_blendshape(
            target_mesh=target_mesh,
            blendshape_name=target_blendshape_name,
        )
    else:
        destination = resolve_blendshape(target_blendshape)

    requested_names = set(target_names or [])

    targets_to_transfer = [
        target for target in source.targets if not requested_names or target.name in requested_names
    ]

    found_names = {target.name for target in targets_to_transfer}

    missing_names = requested_names - found_names

    if missing_names:
        raise ValueError(
            f"The following targets do not exist on {source.node}: {sorted(missing_names)}"
        )

    if not targets_to_transfer:
        raise ValueError(f"No transferable targets found on {source.node}")

    original_source_values = get_weight_values(source)
    original_destination_values = get_weight_values(destination)

    result = BlendShapeTransfer(
        source=source,
        destination=destination,
        proximity_wrap=None,
    )

    temporary_meshes: list[str] = []

    cmds.undoInfo(openChunk=True)

    try:
        zero_blendshape(source)
        zero_blendshape(destination)

        wrap_settings = {
            "falloff_scale": falloff_scale,
            "dropoff_rate_scale": dropoff_rate_scale,
            "smooth_influences": smooth_influences,
            "smooth_normals": smooth_normals,
        }

        filtered_wrap_settings: dict[str, int | float] = {
            setting: value for setting, value in wrap_settings.items() if value is not None
        }

        result.proximity_wrap = create_proximity_wrap(
            driver=source_mesh,
            driven=target_mesh,
            name=f"{destination.node}_transfer_proximityWrap",
            settings=filtered_wrap_settings,
        )

        for source_target in targets_to_transfer:
            destination = get_blendshape_data(destination.node)

            existing_target: ShapeTarget | None = None

            with suppress(ValueError):
                existing_target = destination.get_target(source_target.name)

            if existing_target and not overwrite_existing:
                result.skipped.append(source_target.name)

                cmds.warning(
                    f"Skipping {source_target.name}: it already exists on {destination.node}"
                )
                continue

            source_plug = f"{source.node}.weight[{source_target.index}]"

            cmds.setAttr(source_plug, 1.0)  # type:ignore
            cmds.dgdirty(target_mesh)
            cmds.refresh(force=True)

            temporary_target = cmds.duplicate(
                target_mesh,
                name=f"{source_target.name}_transferTarget",
                returnRootsOnly=True,
            )[0]

            temporary_meshes.append(temporary_target)

            cmds.delete(
                temporary_target,
                constructionHistory=True,
            )

            if existing_target:
                destination_index = existing_target.index

                cmds.blendShape(
                    destination.node,
                    edit=True,
                    target=(
                        target_mesh,
                        destination_index,
                        temporary_target,
                        1.0,
                    ),
                    topologyCheck=True,
                )
            else:
                destination_index = get_next_target_index(destination)

                destination = add_blendshape_target(
                    blendshape=destination,
                    base_mesh=target_mesh,
                    target_mesh=temporary_target,
                    target_name=source_target.name,
                    index=destination_index,
                )

            result.transferred.append(
                TransferredShape(
                    name=source_target.name,
                    source_index=source_target.index,
                    destination_index=destination_index,
                )
            )

            cmds.setAttr(source_plug, 0.0)  # type:ignore

            cmds.delete(temporary_target)
            temporary_meshes.remove(temporary_target)

        result.destination = get_blendshape_data(destination.node)

    finally:
        for temporary_mesh in temporary_meshes:
            if cmds.objExists(temporary_mesh):
                cmds.delete(temporary_mesh)

        set_weight_values(
            source,
            original_source_values,
        )

        set_weight_values(
            get_blendshape_data(destination.node),
            original_destination_values,
        )

        if delete_proximity_wrap and result.proximity_wrap:
            result.proximity_wrap.delete()
            result.proximity_wrap = None

        cmds.undoInfo(closeChunk=True)

    return result
