"""
Serialize and restore Maya blendShape target data.

Notes for future adventures:
The names ``target``, ``group``, and ``item`` refer to Maya's internal
attribute hierarchy.

In particular:

* ``target`` refers to an input geometry slot on the blendShape..

* ``group`` refers to a blendShape weight/alias within that target slot.
  Despite being called a "group" by Maya, this is effectively the named
  blendShape target that an artist sees (for example, ``smile``).

* ``item`` These are the final leaf structures that hold the data to represent
the base target and in-between targets. The base target is stored at index 6000.
This is so that even with only a sparse array, you can write inbetween deltas for
weights from -5 to essentially infinity with 1% increments in precision.
5000 = -1 6000 = 1, 6500 = 1.5 7000 = 2 etc.

Overengineered and weird? Yep :)

The dataclass names intentionally mirror this Maya hierarchy so that the
serialized structure corresponds directly to the underlying attributes.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from pathlib import Path

from maya import cmds
from maya.api.OpenMaya import (
    MFn,
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
from yrig.io.json import export_json, load_json
from yrig.maya_api.attribute import (
    BlendShapeInputTargetAttribute,
    BlendShapeInputTargetGroupAttribute,
    BlendShapeInputTargetItemAttribute,
)
from yrig.maya_api.node import BlendShape
from yrig.maya_api.utils import get_plug


@dataclass
class BlendShapeData:
    name: str
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


def _get_component_indices(plug: MPlug) -> list[int]:
    components_mob: MObject = plug.asMObject()
    fn_components: MFnComponentListData = MFnComponentListData(components_mob)
    component_ids: list[int] = []
    for x in range(fn_components.length()):
        comp_mob = fn_components.get(x)
        fn_comp = MFnSingleIndexedComponent(comp_mob)
        component_ids.extend(fn_comp.getElements())
    return component_ids


def _set_component_indices(plug: MPlug, indices: list[int]) -> None:
    fn_data: MFnComponentListData = MFnComponentListData()
    data_mob: MObject = fn_data.create()
    fn_comp: MFnSingleIndexedComponent = MFnSingleIndexedComponent()
    comp_mob: MObject = fn_comp.create(MFn.kMeshVertComponent)
    fn_comp.addElements(indices)
    fn_data.add(comp_mob)
    plug.setMObject(data_mob)


def _get_point_array(plug: MPlug) -> MPointArray:
    points_mob: MObject = plug.asMObject()
    fn_points: MFnPointArrayData = MFnPointArrayData(points_mob)
    points_array: MPointArray = fn_points.array()
    return points_array


def _set_point_array(plug: MPlug, point_array: MPointArray) -> None:
    fn_points = MFnPointArrayData()
    points_mob = fn_points.create(point_array)
    plug.setMObject(points_mob)


def get_blendshape_target_item_data(
    target_item: BlendShapeInputTargetItemAttribute,
) -> BlendShapeTargetItemData:
    components_plug = get_plug(str(target_item.input_components_target))
    component_ids = _get_component_indices(components_plug)

    points_plug = get_plug(str(target_item.input_points_target))
    points_array = _get_point_array(points_plug)
    points_dict = {
        id: (point.x, point.y, point.z)
        for id, point in zip(component_ids, points_array, strict=True)  # type: ignore
        if not point.isEquivalent(MPoint.kOrigin)
    }
    return BlendShapeTargetItemData(points=points_dict)


def apply_blendshape_target_item_data(
    blendshape: BlendShape,
    data: BlendShapeTargetItemData,
    target_index: int,
    group_index: int,
    item_index: int,
) -> None:
    item_attr = (
        blendshape.input_target[target_index]
        .input_target_group[group_index]
        .input_target_item[item_index]
    )
    component_plug = get_plug(str(item_attr.input_components_target))
    points_plug = get_plug(str(item_attr.input_points_target))

    component_ids: list[int] = []
    point_array: MPointArray = MPointArray()
    point_array.setLength(len(data.points))
    for index, (component_id, point) in enumerate(data.points.items()):
        component_ids.append(component_id)
        point_array[index] = MPoint(*point)

    _set_component_indices(component_plug, component_ids)

    _set_point_array(points_plug, point_array)


def get_blendshape_target_items_dict(
    target_group: BlendShapeInputTargetGroupAttribute,
) -> dict[int, BlendShapeTargetItemData]:
    items: dict[int, BlendShapeTargetItemData] = {}
    for index in target_group.input_target_item.get_indices():
        item = target_group.input_target_item[index]
        item_data = get_blendshape_target_item_data(item)
        items[index] = item_data
    return items


def apply_blendshape_target_items_dict(
    blendshape: BlendShape,
    data: dict[int, BlendShapeTargetItemData],
    target_index: int,
    group_index: int,
) -> None:
    for index, target_item in data.items():
        apply_blendshape_target_item_data(
            blendshape,
            data=target_item,
            target_index=target_index,
            group_index=group_index,
            item_index=index,
        )
        blendshape.input_target[target_index].input_target_group[group_index]


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


def apply_blendshape_target_group_data(
    blendshape: BlendShape,
    data: BlendShapeTargetGroupData,
    target_index: int,
    group_index: int,
) -> None:
    if blendshape.weight[group_index].get_alias() != data.name:
        blendshape.weight[group_index].set_alias(data.name)
    blendshape.weight[group_index].set(0)
    apply_blendshape_target_items_dict(
        blendshape, data.items, target_index=target_index, group_index=group_index
    )


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
        blendshape_node.name,
        inputs={index: data for index, data in enumerate(input_data)},
        targets=target_data,
    )


def apply_blendshape_data(
    blendshape: str | BlendShape, data: BlendShapeData, targets: Collection[str] | None = None
) -> None:
    blendshape_node = (
        blendshape if isinstance(blendshape, BlendShape) else BlendShape.from_existing(blendshape)
    )
    for target_index, target in data.targets.items():
        for group_index, group in target.groups.items():
            if not targets or group.name in targets:
                apply_blendshape_target_group_data(
                    blendshape_node, group, target_index=target_index, group_index=group_index
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


def import_blendshape(
    filepath: Path,
    blendshape: str | BlendShape,
    targets: Collection[str] | None = None,
) -> None:
    data = load_json(filepath, BlendShapeData)
    apply_blendshape_data(blendshape, data, targets)
