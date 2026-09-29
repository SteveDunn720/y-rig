from collections import deque

from yrig.maya_api.node import PoseInterpolatorManagerNode


def get_parent_directory_index_from_name(
    manager: PoseInterpolatorManagerNode, parent_directory: str
) -> int | None:
    """Breadth first search for the given parent directory by name."""
    queue = deque([0])
    while queue:
        current_index = queue.popleft()
        directory = manager.pose_interpolator_directory[current_index]
        directory_name = directory.directory_name.get()
        if directory_name == parent_directory:
            return current_index
        queue.extend(-child_index for child_index in directory.child_indices.get())
    return None


def get_parent_directory_path_from_name(
    manager: PoseInterpolatorManagerNode, parent_directory: str
) -> list[int] | None:
    """Breadth-first search for the given parent directory by name."""
    queue = deque([(0, [0])])
    while queue:
        current_index, path = queue.popleft()
        directory = manager.pose_interpolator_directory[current_index]
        if directory.directory_name.get() == parent_directory:
            return path
        for child_index in directory.child_indices.get():
            queue.append((-child_index, [*path, -child_index]))
    return None


def get_parent_directory_path_from_index(
    manager: PoseInterpolatorManagerNode,
    directory_index: int,
) -> list[int]:
    """Return the path from the root directory to a directory."""
    queue = deque([(0, [0])])
    while queue:
        current_index, path = queue.popleft()
        if current_index == directory_index:
            return path
        directory = manager.pose_interpolator_directory[current_index]
        for child_index in directory.child_indices.get():
            child_index = -child_index
            queue.append((child_index, [*path, child_index]))
    raise ValueError(f"Directory index does not exist: {directory_index}")
