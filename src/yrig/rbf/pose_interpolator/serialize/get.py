from yrig.maya_api.node import PoseInterpolatorManagerNode, PoseInterpolatorNode

from .data import (
    PoseInterpolatorControllerDataItem,
    PoseInterpolatorData,
    PoseInterpolatorDirectoryData,
    PoseInterpolatorDriverData,
    PoseInterpolatorPoseControllerData,
    PoseInterpolatorPoseData,
)


def _str_or_none(value: object | None) -> str | None:
    return None if value is None else str(value)


def get_pose_interpolator_data(
    pose_interpolator: str | PoseInterpolatorNode,
) -> PoseInterpolatorData:
    node = (
        pose_interpolator
        if isinstance(pose_interpolator, PoseInterpolatorNode)
        else PoseInterpolatorNode.from_existing(pose_interpolator)
    )

    drivers = []
    for index in node.driver.get_indices():
        driver = node.driver[index]
        controllers = {
            controller_index: str(driver.driver_controller[controller_index].get_input())
            for controller_index in driver.driver_controller.get_indices()
        }
        drivers.append(
            PoseInterpolatorDriverData(
                matrix=str(driver.driver_matrix.get_input()),
                orient=driver.driver_orient.get(),
                rotate_axis=driver.driver_rotate_axis.get(),
                twist_axis=driver.driver_twist_axis.get(),
                rotate_order=driver.driver_rotate_order.get(),
                euler_twist=driver.driver_euler_twist.get(),
                controllers=controllers,
            )
        )

    poses = []
    for index in node.pose.get_indices():
        pose = node.pose[index]

        controller_data = {}
        for controller_index in pose.pose_controller_data.get_indices():
            controller = pose.pose_controller_data[controller_index]

            items = {}
            for item_index in controller.pose_controller_data.get_indices():
                item = controller.pose_controller_data[item_index]
                items[item_index] = PoseInterpolatorControllerDataItem(
                    name=item.pose_controller_data_item_name.get(),
                    type=item.pose_controller_data_item_type.get(),
                    value=item.pose_controller_data_item_value.get(),
                )

            controller_data[controller_index] = PoseInterpolatorPoseControllerData(
                items=items,
            )

        rotations: list[tuple[float, float, float, float]] = [  # type: ignore
            tuple(pose.pose_rotation[index].get()) for index in pose.pose_rotation.get_indices()
        ]

        translations: list[tuple[float, float, float]] = [  # type: ignore
            tuple(pose.pose_translation[index].get())
            for index in pose.pose_translation.get_indices()
        ]

        poses.append(
            PoseInterpolatorPoseData(
                name=pose.pose_name.get(),
                rotations=rotations,
                translations=translations,
                independent=pose.is_independent.get(),
                rotation_falloff=pose.pose_rotation_falloff.get(),
                translation_falloff=pose.pose_translation_falloff.get(),
                pose_type=pose.pose_type.get(),
                gaussian_falloff=pose.pose_falloff.get(),
                is_enabled=pose.is_enabled.get(),
                controller_data=controller_data,
            )
        )

    outputs = [[str(attr) for attr in output.get_outputs()] for output in node.output]
    return PoseInterpolatorData(
        name=node.name,
        allow_negative_weights=node.allow_negative_weights.get(),
        enable_rotation=node.enable_rotation.get(),
        enable_translation=node.enable_translation.get(),
        interpolation=node.interpolation.get(),
        output_smoothing=node.output_smoothing.get(),
        regularization=node.regularization.get(),
        drivers=drivers,
        poses=poses,
        outputs=outputs,
    )


def _get_pose_interpolator_directory_data(
    manager: PoseInterpolatorManagerNode, index: int
) -> PoseInterpolatorDirectoryData:
    directory = manager.pose_interpolator_directory[index]
    child_indices = directory.child_indices.get()
    directories = []
    pose_interpolators = []
    for child_index in child_indices:
        if child_index < 0:
            directories.append(_get_pose_interpolator_directory_data(manager, -child_index))
        else:
            parent_attr = manager.pose_interpolator_parent[child_index]
            source_attr = parent_attr.get_input()
            if source_attr is None:
                raise RuntimeError(f"Couldn't find a poseInterpolator connected to {source_attr}")
            source_node = str(source_attr).split(".", 1)[0]
            pose_interpolators.append(get_pose_interpolator_data(source_node))

    return PoseInterpolatorDirectoryData(
        name=directory.directory_name.get(),
        directories=directories,
        pose_interpolators=pose_interpolators,
    )


def get_pose_interpolator_directory_data(index: int = 0) -> PoseInterpolatorDirectoryData:
    manager = PoseInterpolatorManagerNode.from_existing("poseInterpolatorManager")
    return _get_pose_interpolator_directory_data(manager, index)
