import re

LEFT_SIDE_NAME = "L"
RIGHT_SIDE_NAME = "R"
MIDDLE_SIDE_NAME = "M"
SIDE_NAMES: tuple[str, ...] = (LEFT_SIDE_NAME, RIGHT_SIDE_NAME, MIDDLE_SIDE_NAME)

GET_SIDE_REGEX = re.compile(rf"(?<=_)(?:{'|'.join(SIDE_NAMES)})(?=_|$)")
LEFT_SIDE_REGEX = re.compile(rf"(?<=_){LEFT_SIDE_NAME}(?=_|$)")
RIGHT_SIDE_REGEX = re.compile(rf"(?<=_){RIGHT_SIDE_NAME}(?=_|$)")


def get_side(name: str) -> str | None:
    """
    Extracts the side token from a control name. eg. Front_Leg_L_CTL will return "L"
    Valid sides: ["L", "R", "M"]
    Args:
        name: The control name.
    Returns:
        The side token found in the name, or None if not found.
    """
    # Create a pattern that matches any of the sides preceded by "_" and followed by "_" or end of string
    match = re.search(GET_SIDE_REGEX, name)
    return match.group(0) if match else None


def flip_side(name: str) -> str:
    """
    Replaces side token in the name from 'L' to 'R' or vice versa,
    only when it's a distinct token (e.g., 'Front_Leg_L' becomes 'Front_Leg_R').

    Args:
        name: The original name.
    Returns:
        The renamed string.
    """
    flip_name = re.sub(LEFT_SIDE_REGEX, RIGHT_SIDE_NAME, name)
    flip_name = re.sub(RIGHT_SIDE_REGEX, LEFT_SIDE_NAME, name)
    return flip_name


def get_short_name(transform: str) -> str:
    """Return the leaf node name from a DAG path, stripping all parent namespaces.

    Maya DAG paths use ``|`` as a separator (e.g. ``|group1|joint1``).
    This function returns only the last component of such a path.

    Args:
        transform: A full or partial Maya DAG path string.

    Returns:
        The short (leaf) name without any leading path components.
    """
    return transform.rsplit("|", 1)[-1]
