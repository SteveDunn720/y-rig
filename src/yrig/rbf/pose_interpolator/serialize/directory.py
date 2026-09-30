from collections import deque
from dataclasses import replace

from yrig.maya_api.node import PoseInterpolatorManagerNode
from yrig.rbf.pose_interpolator.core import resolve_pose_interpolator_shape
from yrig.transform import get_transform

from .data import (
    PoseInterpolatorData,
    PoseInterpolatorDirectoryData,
)


def get_directory_indices(
    manager: PoseInterpolatorManagerNode,
    directories: set[str],
    start_index: int = 0,
) -> dict[str, int]:
    """
    Breadth first search for the given directories.
    """
    indices_map: dict[str, int] = {}
    visited: set[int] = set()
    queue = deque([start_index])
    while queue:
        current_index = queue.popleft()
        if current_index in visited:
            continue
        visited.add(current_index)

        if current_index > 0:
            continue
        else:
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
    visited: set[int] = set()
    queue = deque([start_index])
    while queue:
        current_index = queue.popleft()
        if current_index in visited:
            continue
        visited.add(current_index)

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
        else:
            directory_index = -current_index
            directory = manager.pose_interpolator_directory[directory_index]
            queue.extend(child_index for child_index in directory.child_indices.get())

    missing = pose_interpolators - indices_map.keys()
    if missing:
        raise RuntimeError(f"poseInterpolators not found: {', '.join(sorted(missing))}")

    return indices_map


def _find_in_directory_data(
    root: PoseInterpolatorDirectoryData,
    directory_names: set[str],
    pose_interpolator_names: set[str],
) -> tuple[
    dict[str, PoseInterpolatorDirectoryData],
    dict[str, PoseInterpolatorData],
    dict[int, PoseInterpolatorDirectoryData | None],
]:
    """
    Breadth first search of the file data for the given directories and poseInterpolators
    (shape or transform name).

    Returns the found directories, the found poseInterpolators, and a map of
    id(node) -> parent directory for every node visited, used to walk up to ancestors.
    """
    found_directories: dict[str, PoseInterpolatorDirectoryData] = {}
    found_pose_interpolators: dict[str, PoseInterpolatorData] = {}
    parents: dict[int, PoseInterpolatorDirectoryData | None] = {id(root): None}

    queue = deque([root])
    while queue:
        current = queue.popleft()

        if current.name in directory_names and current.name not in found_directories:
            found_directories[current.name] = current

        for pose_interpolator_data in current.pose_interpolators:
            parents[id(pose_interpolator_data)] = current
            # Data stores the shape name; users may pass shape or transform name.
            names = {pose_interpolator_data.name, pose_interpolator_data.name.removesuffix("Shape")}
            for match in (names & pose_interpolator_names) - found_pose_interpolators.keys():
                found_pose_interpolators[match] = pose_interpolator_data

        # Early exit if everything requested has been found
        if len(found_directories) == len(directory_names) and len(found_pose_interpolators) == len(
            pose_interpolator_names
        ):
            break

        for child in current.directories:
            parents[id(child)] = current
            queue.append(child)

    if missing := directory_names - found_directories.keys():
        raise RuntimeError(f"Directories not found in file: {', '.join(sorted(missing))}")
    if missing := pose_interpolator_names - found_pose_interpolators.keys():
        raise RuntimeError(f"poseInterpolators not found in file: {', '.join(sorted(missing))}")

    return found_directories, found_pose_interpolators, parents


def _without_selected(
    node: PoseInterpolatorDirectoryData,
    selected_ids: set[int],
) -> PoseInterpolatorDirectoryData:
    """
    Copy a subtree, dropping any directly selected descendants
    """
    return replace(
        node,
        directories=[
            _without_selected(child, selected_ids)
            for child in node.directories
            if id(child) not in selected_ids
        ],
        pose_interpolators=[
            pose_interpolator_data
            for pose_interpolator_data in node.pose_interpolators
            if id(pose_interpolator_data) not in selected_ids
        ],
    )


def filter_pose_interpolator_directory_data(
    data: PoseInterpolatorDirectoryData,
    directories: set[str] | None = None,
    pose_interpolators: set[str] | None = None,
) -> PoseInterpolatorDirectoryData:
    """
    Hoist the requested directories (with everything below them) and poseInterpolators
    out of the tree into a new root, discarding their original ancestors.
    """
    if directories is None and pose_interpolators is None:
        return data

    found_directories, found_pose_interpolators, _ = _find_in_directory_data(
        data, set(directories or ()), set(pose_interpolators or ())
    )

    selected_ids = {id(node) for node in found_directories.values()} | {
        id(node) for node in found_pose_interpolators.values()
    }

    return replace(
        data,
        directories=[_without_selected(node, selected_ids) for node in found_directories.values()],
        pose_interpolators=list(found_pose_interpolators.values()),
    )
