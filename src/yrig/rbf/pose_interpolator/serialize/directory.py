from collections import deque

from yrig.maya_api.node import PoseInterpolatorManagerNode
from yrig.rbf.pose_interpolator.core import resolve_pose_interpolator_shape
from yrig.transform import get_transform


def get_directory_indices(
    manager: PoseInterpolatorManagerNode,
    directories: set[str],
    start_index: int = 0,
) -> dict[str, int]:
    """
    Breadth first search for the given directories.
    """
    indices_map: dict[str, int] = {}
    queue = deque([start_index])
    while queue:
        current_index = queue.popleft()
        if current_index > 0:
            continue
        directory_index = -current_index
        directory = manager.pose_interpolator_directory[directory_index]
        directory_name = directory.directory_name.get()
        if directory_name in directories and directory_name not in indices_map:
            indices_map[directory_name] = directory_index
            # Early exit if all target directories have been found
            if len(indices_map) == len(directories):
                return indices_map

        queue.extend(child_index for child_index in directory.child_indices.get())

    missing = directories - indices_map.keys()
    if missing:
        raise RuntimeError(f"Directories not found: {', '.join(sorted(missing))}")

    return indices_map


def get_pose_interpolator_indices(
    manager: PoseInterpolatorManagerNode,
    pose_interpolators: set[str],
    start_index: int = 0,
) -> dict[str, int]:
    """
    Breadth first search for the given poseInterpolators (shape or transform name).
    """
    indices_map: dict[str, int] = {}
    queue = deque([start_index])
    while queue:
        current_index = queue.popleft()
        if current_index > 0:
            parent_attr = manager.pose_interpolator_parent[current_index]
            source_attr = parent_attr.get_input()
            if source_attr is None:
                raise RuntimeError(f"Couldn't find a poseInterpolator connected to {source_attr}")
            source_node = str(source_attr).split(".", 1)[0]
            pose_interpolator_shape = resolve_pose_interpolator_shape(source_node)
            pose_interpolator_transform = get_transform(pose_interpolator_shape)
            matches = {pose_interpolator_shape, pose_interpolator_transform} & pose_interpolators
            if matches:
                pose_interpolator_match = next(iter(matches))
                indices_map[pose_interpolator_match] = current_index
            continue
        directory_index = -current_index
        directory = manager.pose_interpolator_directory[directory_index]
        queue.extend(child_index for child_index in directory.child_indices.get())

    missing = pose_interpolators - indices_map.keys()
    if missing:
        raise RuntimeError(f"poseInterpolators not found: {', '.join(sorted(missing))}")

    return indices_map
