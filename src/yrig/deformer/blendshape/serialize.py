from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from maya import cmds
from maya.api.OpenMaya import (
    MFnComponentListData,
    MFnPointArrayData,
    MFnSingleIndexedComponent,
    MObject,
    MPlug,
    MPoint,
    MPointArray,
)

from yrig.deformer.blendshape.core import resolve_target_index
from yrig.io import confirm_overwrite
from yrig.io.json import export_json
from yrig.maya_api.attribute import (
    BlendShapeInputTargetAttribute,
    BlendShapeInputTargetGroupAttribute,
    BlendShapeInputTargetItemAttribute,
)
from yrig.maya_api.node import BlendShape
from yrig.maya_api.utils import get_plug


@dataclass
class BlendShapeData:
    inputs: dict[int, BlendShapeInputData]
    targets: dict[int, BlendShapeInputTargetData]


@dataclass
class BlendShapeInputData:
    geometry: str
    original_geometry: str | None
    group_id: int = 0
    component_tag_expression: str = "*"


@dataclass
class BlendShapeInputTargetData:
    groups: dict[int, BlendShapeTargetGroupData]


@dataclass
class BlendShapeTargetGroupData:
    name: str
    items: dict[int, BlendShapeTargetItemData]


@dataclass
class BlendShapeTargetItemData:
    points: dict[int, tuple[float, float, float]]


def _get_component_indices_from_plug(plug: MPlug) -> list[int]:
    components_mob: MObject = plug.asMObject()
    fn_components: MFnComponentListData = MFnComponentListData(components_mob)
    component_ids: list[int] = []
    for x in range(fn_components.length()):
        comp_mob = fn_components.get(x)
        fn_comp = MFnSingleIndexedComponent(comp_mob)
        component_ids.extend(fn_comp.getElements())
    return component_ids


def get_blendshape_target_item_data(
    target_item: BlendShapeInputTargetItemAttribute,
) -> BlendShapeTargetItemData:
    components_plug = get_plug(str(target_item.input_components_target))
    component_ids = _get_component_indices_from_plug(components_plug)

    points_plug = get_plug(str(target_item.input_points_target))
    points_mob: MObject = points_plug.asMObject()
    fn_points: MFnPointArrayData = MFnPointArrayData(points_mob)
    points_array: MPointArray = fn_points.array()
    points_dict = {
        id: (point.x, point.y, point.z)
        for id, point in zip(component_ids, points_array, strict=True)  # type: ignore
        if point.isEquivalent(MPoint.kOrigin)
    }
    return BlendShapeTargetItemData(points=points_dict)


def get_blendshape_target_items_dict(
    target_group: BlendShapeInputTargetGroupAttribute,
) -> dict[int, BlendShapeTargetItemData]:
    items: dict[int, BlendShapeTargetItemData] = {}
    for index in target_group.input_target_item.get_indices():
        item = target_group.input_target_item[index]
        item_data = get_blendshape_target_item_data(item)
        items[index] = item_data
    return items


def get_target_name_map(blendshape: BlendShape) -> dict[int, str]:
    aliases = cmds.aliasAttr(str(blendshape), query=True) or []
    return {
        int(attr.removeprefix("weight[").removesuffix("]")): alias
        for alias, attr in zip(aliases[::2], aliases[1::2], strict=True)
    }


def get_blendshape_target_groups_dict(
    blendshape: BlendShape, target: BlendShapeInputTargetAttribute
) -> dict[int, BlendShapeTargetGroupData]:
    target_groups: dict[int, BlendShapeTargetGroupData] = {}
    alias_map = get_target_name_map(blendshape)
    for index in target.input_target_group.get_indices():
        target_group = target.input_target_group[index]
        target_name = alias_map[index]
        target_group_data = BlendShapeTargetGroupData(
            name=target_name, items=get_blendshape_target_items_dict(target_group)
        )
        target_groups[index] = target_group_data

    return target_groups


def get_blendshape_target_dict(
    blendshape: BlendShape, targets: Iterable[int] | None = None
) -> dict[int, BlendShapeInputTargetData]:
    target_data_dict: dict[int, BlendShapeInputTargetData] = {}
    indices = targets if targets is not None else blendshape.input.get_indices()
    for index in indices:
        target = blendshape.input_target[index]
        group_data = get_blendshape_target_groups_dict(blendshape, target)
        target_data = BlendShapeInputTargetData(groups=group_data)
        if target_data.groups:
            target_data_dict[index] = target_data
    return target_data_dict


def get_blendshape_input_data_list(
    blendshape: BlendShape, targets: Iterable[int] | None = None
) -> list[BlendShapeInputData]:
    inputs: list[BlendShapeInputData] = []
    indices = targets if targets is not None else blendshape.input.get_indices()
    for index in indices:
        input = blendshape.input[index]
        input_geo = input.input_geometry.get_input()
        original_geo = blendshape.original_geometry[index].get_input()
        if input_geo:
            input_data = BlendShapeInputData(
                str(input_geo),
                original_geometry=str(original_geo) if original_geo else None,
                group_id=input.group_id.get(),
                component_tag_expression=input.component_tag_expression.get(),
            )
            inputs.append(input_data)
    return inputs


def get_blendshape_data(
    blendshape: str | BlendShape, targets: Iterable[str | int] | None = None
) -> BlendShapeData:
    blendshape_node = (
        blendshape if isinstance(blendshape, BlendShape) else BlendShape.from_existing(blendshape)
    )
    targets_to_export = (
        [resolve_target_index(str(blendshape), target) for target in targets]
        if targets is not None
        else None
    )
    input_data = get_blendshape_input_data_list(blendshape_node, targets=targets_to_export)
    target_data = get_blendshape_target_dict(blendshape_node, targets=targets_to_export)
    return BlendShapeData(
        inputs={index: data for index, data in enumerate(input_data)}, targets=target_data
    )


def export_blendshape(
    filepath: Path,
    blendshape: str | BlendShape,
    targets: Iterable[str | int] | None = None,
    force: bool = False,
) -> bool:
    if not confirm_overwrite(filepath, force):
        return False
    blendshape_data = get_blendshape_data(blendshape, targets)
    export_json(filepath, blendshape_data)
    return True
