from yrig.maya_api.node import QuatNormalizeNode, QuatToEulerNode
from yrig.name import get_short_name
from yrig.transform.matrix import localize_and_decompose_matrix
from yrig.transform.utils import Axis


def twist_extract_euler(transform: str, parent: str, axis: Axis) -> QuatToEulerNode:
    """
    Extract the twist of a transform around a specified axis and
    output it as Euler angles.
    Args:
        transform: Name of the transform whose twist should be extracted.
        parent: Transform used as the reference space for the twist.
        axis: Axis around which the twist should be isolated ("x", "y", or "z").

    Returns:
        QuatToEulerNode: Node producing the extracted twist as Euler rotation.
    """
    name = f"{get_short_name(transform)}_twist"
    decompose = localize_and_decompose_matrix(transform, parent)
    euler_output = QuatToEulerNode(f"{name}_euler")
    decompose.output_quat.w.connect_to(euler_output.input_quat.w)
    if axis == "x":
        decompose.output_quat.x.connect_to(euler_output.input_quat.x)
    elif axis == "y":
        decompose.output_quat.y.connect_to(euler_output.input_quat.y)
    elif axis == "z":
        decompose.output_quat.z.connect_to(euler_output.input_quat.z)
    return euler_output


def twist_extract_quat(transform: str, parent: str, axis: Axis) -> QuatNormalizeNode:
    """
    Extract the twist of a transform around a specified axis and
    output it as a normalized quaternion.
    Args:
        transform: Name of the transform whose twist should be extracted.
        parent: Transform used as the reference space for the twist.
        axis: Axis around which the twist should be isolated ("x", "y", or "z").

    Returns:
        QuatNormalizeNode: Node producing the extracted twist as a normalized
        quaternion.
    """
    name = f"{get_short_name(transform)}_twist"
    decompose = localize_and_decompose_matrix(transform, parent)
    output = QuatNormalizeNode(name)
    decompose.output_quat.w.connect_to(output.input_quat.w)
    if axis == "x":
        decompose.output_quat.x.connect_to(output.input_quat.x)
    elif axis == "y":
        decompose.output_quat.y.connect_to(output.input_quat.y)
    elif axis == "z":
        decompose.output_quat.z.connect_to(output.input_quat.z)
    return output
