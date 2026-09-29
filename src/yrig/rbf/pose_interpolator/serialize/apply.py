import logging

from maya import cmds

from yrig.maya_api.attribute import Attribute
from yrig.maya_api.node import PoseInterpolatorManagerNode, PoseInterpolatorNode
from yrig.transform import get_transform

from .data import (
    PoseInterpolatorData,
    PoseInterpolatorDirectoryData,
)

log = logging.getLogger(__name__)


def _apply_attribute(
    attribute: Attribute,
    source: Attribute | str,
    value: object,
) -> None:
    """Connect an attribute when possible, otherwise set its value."""
    try:
        attribute.connect_from(source)
    except Exception:
        attribute.set(value)


def apply_pose_interpolator_data(
    pose_interpolator: str | PoseInterpolatorNode,
    data: PoseInterpolatorData,
) -> None:
    node = (
        pose_interpolator
        if isinstance(pose_interpolator, PoseInterpolatorNode)
        else PoseInterpolatorNode.from_existing(pose_interpolator)
    )

    node.allow_negative_weights.set(data.allow_negative_weights)
    node.enable_rotation.set(data.enable_rotation)
    node.enable_translation.set(data.enable_translation)
    node.interpolation.set(data.interpolation)
    node.output_smoothing.set(data.output_smoothing)
    node.regularization.set(data.regularization)

    node.driver.clear()
    for index, driver_data in enumerate(data.drivers):
        driver = node.driver[index]

        driver_node = driver_data.matrix.split(".", 1)[0]
        driver.driver_matrix.connect_from(driver_data.matrix)
        _apply_attribute(driver.driver_orient, f"{driver_node}.jointOrient", driver_data.orient)
        _apply_attribute(
            driver.driver_rotate_axis, f"{driver_node}.rotateAxis", driver_data.rotate_axis
        )
        driver.driver_twist_axis.set(driver_data.twist_axis)
        _apply_attribute(
            driver.driver_rotate_order, f"{driver_node}.rotateOrder", driver_data.rotate_order
        )
        driver.driver_euler_twist.set(driver_data.euler_twist)

        for controller_index, value in driver_data.controllers.items():
            driver.driver_controller[controller_index].set(value)

    node.pose.clear()
    for index, pose_data in enumerate(data.poses):
        pose = node.pose[index]
        pose.pose_name.set(pose_data.name)
        for index, rotation in enumerate(pose_data.rotations):
            pose.pose_rotation[index].set(rotation)
        for index, translation in enumerate(pose_data.translations):
            pose.pose_translation[index].set(translation)
        pose.is_independent.set(pose_data.independent)
        pose.pose_rotation_falloff.set(pose_data.rotation_falloff)
        pose.pose_translation_falloff.set(pose_data.translation_falloff)
        pose.pose_type.set(pose_data.pose_type)
        pose.pose_falloff.set(pose_data.gaussian_falloff)
        pose.is_enabled.set(pose_data.is_enabled)

        for controller_index, controller_data in pose_data.controller_data.items():
            controller = pose.pose_controller_data[controller_index]

            for item_index, item_data in controller_data.items.items():
                item = controller.pose_controller_data[item_index]
                item.pose_controller_data_item_name.set(item_data.name)
                item.pose_controller_data_item_type.set(item_data.type)
                item.pose_controller_data_item_value.set(item_data.value)

    for index, output in enumerate(data.outputs):
        output_attr = node.output[index]
        desired_connections = set(output)
        current_connections = {str(attr) for attr in output_attr.get_outputs()}
        for destination in current_connections - desired_connections:
            output_attr.disconnect_from(destination)

        for destination in desired_connections - current_connections:
            try:
                output_attr.connect_to(destination)
            except Exception:
                log.warning(
                    "Couldn't connect %s to the destination specified in the data: %s",
                    output_attr,
                    destination,
                )


def add_pose_interpolator(
    manager: PoseInterpolatorManagerNode,
    data: PoseInterpolatorData,
    parent: str | None = None,
    parent_directory_index: int = 0,
) -> tuple[str, PoseInterpolatorNode]:
    """Add poseInterpolator to manager and apply data. Returns the transform and shape node of the created poseInterpolator."""
    pose_interpolator = PoseInterpolatorNode(name=data.name)
    pose_interpolator_transform = get_transform(str(pose_interpolator))
    pose_interpolator_transform = cmds.rename(
        pose_interpolator_transform, data.name.removesuffix("Shape")
    )
    if parent is not None:
        cmds.parent(pose_interpolator_transform, parent)
    target_index = manager.pose_interpolator_parent.next_available_index()
    parent_directory = manager.pose_interpolator_directory[parent_directory_index]
    original_child_indices = parent_directory.child_indices.get()
    apply_pose_interpolator_data(pose_interpolator, data)
    parent_directory.child_indices.set([*original_child_indices, target_index])
    return pose_interpolator_transform, pose_interpolator


def add_pose_interpolator_directory(
    manager: PoseInterpolatorManagerNode,
    data: PoseInterpolatorDirectoryData,
    parent_directory_index: int,
) -> int:
    """Add poseInterpolator directory to manager and apply data. Returns the index at which the poseInterpolator directory was added."""
    directory_index = manager.pose_interpolator_directory.next_available_index()
    directory = manager.pose_interpolator_directory[directory_index]

    directory.directory_name.set(data.name)
    directory.parent_index.set(parent_directory_index)
    parent_directory_child_indices = manager.pose_interpolator_directory[
        parent_directory_index
    ].child_indices.get()

    new_child_indices = [*parent_directory_child_indices, -directory_index]
    manager.pose_interpolator_directory[parent_directory_index].child_indices.set(new_child_indices)
    return directory_index
