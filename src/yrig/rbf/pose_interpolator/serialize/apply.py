import logging

from yrig.maya_api.node import PoseInterpolatorNode

from .data import (
    PoseInterpolatorData,
)

log = logging.getLogger(__name__)


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

        # TODO: make this connect all the values. If it's not possible to do so, then set the static values.
        driver_node = driver_data.matrix.split(".", 1)[0]
        driver.driver_matrix.connect_from(driver_data.matrix)
        driver.driver_orient.set(driver_data.orient)
        driver.driver_rotate_axis.set(driver_data.rotate_axis)
        driver.driver_twist_axis.set(driver_data.twist_axis)
        driver.driver_rotate_order.set(driver_data.rotate_order)
        driver.driver_euler_twist.set(driver_data.euler_twist)

        for controller_index, value in driver_data.controllers.items():
            driver.driver_controller[controller_index].set(value)

    node.pose.clear()
    for index, pose_data in enumerate(data.poses):
        pose = node.pose[index]
        pose.pose_name.set(pose_data.name)
        for index, rotation in enumerate(pose_data.rotations):
            pose.pose_rotation[index].set(rotation)
        for index, rotation in enumerate(pose_data.rotations):
            pose.pose_rotation[index].set(rotation)
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
