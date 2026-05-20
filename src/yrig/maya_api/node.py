import maya.cmds as cmds

from yrig.maya_api.attribute import (
    AimMatrixAxisAttribute,
    AxisAttribute,
    BooleanAttribute,
    ClosestPointOnSurfaceResultAttribute,
    ColorAttribute,
    ConditionOperationAttribute,
    EnumAttribute,
    GeometryAttribute,
    IndexableBlendMatrixTargetAttribute,
    IndexableMatrixAttribute,
    IndexableScalarAttribute,
    IndexableUvPinCoordinateAttribute,
    IndexableVector2Attribute,
    IndexableVector3Attribute,
    IndexableWtMatrixAttribute,
    IntegerAttribute,
    MatrixAttribute,
    MessageAttribute,
    MotionPathWorldUpTypeAttribute,
    MultiplyDivideOperationAttribute,
    NurbsCurveAttribute,
    NurbsSurfaceAttribute,
    PlusMinusAverageOperationAttribute,
    QuatAttribute,
    RotateOrderAttribute,
    ScalarAttribute,
    StringAttribute,
    UnsignedAxisAttribute,
    UvPinNormalOverrideAttribute,
    UvPinRelativeSpaceModeAttribute,
    Vector2Attribute,
    Vector3Attribute,
    Vector4Attribute,
)
from yrig.maya_api.utils import ensure_plugin_loaded

from .version import MAYA_API_VERSION, TARGET_API_VERSION


def is_maya2026_or_newer() -> bool:
    return MAYA_API_VERSION >= 20260000


def is_target_2026_or_newer() -> bool:
    return TARGET_API_VERSION >= 20260000


# Mapping of Node -> Actual name depending on maya version
NODE_TYPES: dict[str, dict[str, str]] = {
    "absolute": {"standard": "absolute", "DL": "absoluteDL"},
    "multiply": {"standard": "multiply", "DL": "multiplyDL"},
    "subtract": {"standard": "subtract", "DL": "subtractDL"},
    "sum": {"standard": "sum", "DL": "sumDL"},
    "sin": {"standard": "sin", "DL": "sinDL"},
    "cos": {"standard": "cos", "DL": "cosDL"},
    "divide": {"standard": "divide", "DL": "divideDL"},
    "clampRange": {"standard": "clampRange", "DL": "clampRangeDL"},
    "distanceBetween": {"standard": "distanceBetween", "DL": "distanceBetweenDL"},
    "crossProduct": {"standard": "crossProduct", "DL": "crossProductDL"},
    "length": {"standard": "length", "DL": "lengthDL"},
    "lerp": {"standard": "lerp", "DL": "lerpDL"},
    "rowFromMatrix": {"standard": "rowFromMatrix", "DL": "rowFromMatrixDL"},
    "multiplyPointByMatrix": {
        "standard": "multiplyPointByMatrix",
        "DL": "multiplyPointByMatrixDL",
    },
    "multiplyVectorByMatrix": {
        "standard": "multiplyVectorByMatrix",
        "DL": "multiplyVectorByMatrixDL",
    },
    "normalize": {"standard": "normalize", "DL": "normalizeDL"},
}

# Mapping of Node -> Required Plugin
NODE_PLUGINS: dict[str, str] = {
    "inverseMatrix": "matrixNodes",
    "transposeMatrix": "matrixNodes",
    "quatToEuler": "quatNodes",
    "eulerToQuat": "quatNodes",
    "quatToAxisAngle": "quatNodes",
    "axisAngleToQuat": "quatNodes",
    "quatInvert": "quatNodes",
    "quatConjugate": "quatNodes",
    "quatNegate": "quatNodes",
    "quatNormalize": "quatNodes",
    "quatAdd": "quatNodes",
    "quatSub": "quatNodes",
    "quatProd": "quatNodes",
    "quatSlerp": "quatNodes",
}


class Node:
    """Base class for all Maya nodes."""

    def __init__(self, node_type: str, name: str | None = None) -> None:
        """
        Initialize a Maya node with version compatibility.

        Args:
            node_type: The base Maya node type (e.g., "multiply", "sum")
            name: Optional custom name for the node
        """
        self.node_type: str = node_type
        self.name: str = self._create_node(node_type, name=name or node_type)

        self.message = MessageAttribute(f"{self.name}.message")

        self._setup_attributes()

    def _ensure_plugin(self, node_type: str) -> None:
        plugin: str | None = NODE_PLUGINS.get(node_type)
        if plugin is not None:
            ensure_plugin_loaded(plugin)

    def _resolve_node_type(self, node_type: str) -> str:
        if node_type in NODE_TYPES:
            types = NODE_TYPES[node_type]
            if is_maya2026_or_newer() and not is_target_2026_or_newer():
                return types["DL"]
            else:
                return types["standard"]
        else:
            return node_type

    def _create_node(self, node_type: str, name: str) -> str:
        """Create the Maya node with appropriate version handling."""
        resolved_type = self._resolve_node_type(node_type)
        self._ensure_plugin(resolved_type)
        return cmds.createNode(resolved_type, name=name)

    def _setup_attributes(self) -> None:
        """Override in subclasses to define node-specific attributes."""
        pass

    def delete(self) -> None:
        """Delete this node."""
        if cmds.objExists(self.name):
            cmds.delete(self.name)

    def exists(self) -> bool:
        """Check if this node exists in Maya."""
        return cmds.objExists(self.name)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"

    def __str__(self) -> str:
        return self.name


class AbsoluteNode(Node):
    """Maya absolute node with enhanced interface."""

    def __init__(self, name: str = "absolute") -> None:
        super().__init__("absolute", name)

    def _setup_attributes(self) -> None:
        self.input = ScalarAttribute(f"{self.name}.input")
        self.output = ScalarAttribute(f"{self.name}.output")


class AddDLNode(Node):
    """Maya addDL node with enhanced interface."""

    def __init__(self, name: str = "addDL") -> None:
        super().__init__("addDL", name)

    def _setup_attributes(self) -> None:
        self.input_1 = ScalarAttribute(f"{self.name}.input1")
        self.input_2 = ScalarAttribute(f"{self.name}.input2")
        self.output = ScalarAttribute(f"{self.name}.output")


class AimMatrixNode(Node):
    """Maya aimMatrix node with enhanced interface."""

    def __init__(self, name: str = "aimMatrix") -> None:
        super().__init__("aimMatrix", name)

    def _setup_attributes(self) -> None:
        self.input_matrix = MatrixAttribute(f"{self.name}.inputMatrix")
        self.primary = AimMatrixAxisAttribute(f"{self.name}.primary", "primary")
        self.secondary = AimMatrixAxisAttribute(f"{self.name}.secondary", "secondary")
        self.output_matrix = MatrixAttribute(f"{self.name}.outputMatrix")


class AxisFromMatrixNode(Node):
    """Maya axisFromMatrix node with enhanced interface."""

    def __init__(self, name: str = "axisFromMatrix") -> None:
        super().__init__("axisFromMatrix", name)

    def _setup_attributes(self) -> None:
        self.input = MatrixAttribute(f"{self.name}.input")
        self.axis = AxisAttribute(f"{self.name}.axis")
        self.output = Vector3Attribute(f"{self.name}.output")


class BlendMatrixNode(Node):
    """Maya blendMatrix node with enhanced interface."""

    def __init__(self, name: str = "blendMatrix") -> None:
        super().__init__("blendMatrix", name)

    def _setup_attributes(self) -> None:
        self.input_matrix = MatrixAttribute(f"{self.name}.inputMatrix")
        self.post_space_matrix = MatrixAttribute(f"{self.name}.postSpaceMatrix")
        self.pre_space_matrix = MatrixAttribute(f"{self.name}.preSpaceMatrix")
        self.target = IndexableBlendMatrixTargetAttribute(f"{self.name}.target")
        self.output_matrix = MatrixAttribute(f"{self.name}.outputMatrix")


class BlendColorsNode(Node):
    """Maya blendColors node with enhanced interface."""

    def __init__(self, name: str = "blendColors") -> None:
        super().__init__("blendColors", name)

    def _setup_attributes(self) -> None:
        self.color1: ColorAttribute = ColorAttribute(f"{self.name}.color1")
        self.color2: ColorAttribute = ColorAttribute(f"{self.name}.color2")
        self.output: ColorAttribute = ColorAttribute(f"{self.name}.output")
        self.blender = ScalarAttribute(f"{self.name}.blender")


class ClampRangeNode(Node):
    """Maya clampRange node with enhanced interface."""

    def __init__(self, name: str = "clampRange") -> None:
        super().__init__("clampRange", name)

    def _setup_attributes(self) -> None:
        self.input = ScalarAttribute(f"{self.name}.input")
        self.minimum = ScalarAttribute(f"{self.name}.minimum")
        self.maximum = ScalarAttribute(f"{self.name}.maximum")
        self.output = ScalarAttribute(f"{self.name}.output")


class ClosestPointOnSurfaceNode(Node):
    """Maya closestPointOnSurface node with enhanced interface."""

    def __init__(self, name: str = "closestPointOnSurface") -> None:
        super().__init__("closestPointOnSurface", name)

    def _setup_attributes(self) -> None:
        self.input_surface = NurbsSurfaceAttribute(f"{self.name}.inputSurface")
        self.in_position = Vector3Attribute(f"{self.name}.inPosition")
        self.result = ClosestPointOnSurfaceResultAttribute(f"{self.name}.result")


class ComposeMatrixNode(Node):
    """Maya composeMatrix node with enhanced interface."""

    def __init__(self, name: str = "composeMatrix") -> None:
        super().__init__("composeMatrix", name)

    def _setup_attributes(self) -> None:

        self.input_rotate_order = RotateOrderAttribute(f"{self.name}.inputRotateOrder")
        self.input_quat = QuatAttribute(f"{self.name}.inputQuat")
        self.input_rotate = Vector3Attribute(f"{self.name}.inputRotate")
        self.input_scale = Vector3Attribute(f"{self.name}.inputScale")
        self.input_shear = Vector3Attribute(f"{self.name}.inputShear")
        self.input_translate = Vector3Attribute(f"{self.name}.inputTranslate")
        self.output_matrix = MatrixAttribute(f"{self.name}.outputMatrix")


class ConditionNode(Node):
    """Maya condition node with enhanced interface."""

    def __init__(self, name: str = "condition") -> None:
        super().__init__("condition", name)

    def _setup_attributes(self) -> None:
        self.first_term: ScalarAttribute = ScalarAttribute(f"{self.name}.firstTerm")
        self.second_term: ScalarAttribute = ScalarAttribute(f"{self.name}.secondTerm")
        self.color_if_true: ColorAttribute = ColorAttribute(f"{self.name}.colorIfTrue")
        self.color_if_false: ColorAttribute = ColorAttribute(f"{self.name}.colorIfFalse")
        self.operation: ConditionOperationAttribute = ConditionOperationAttribute(
            f"{self.name}.operation"
        )
        self.out_color: ColorAttribute = ColorAttribute(f"{self.name}.outColor")


class CosNode(Node):
    """Maya cos node with enhanced interface."""

    def __init__(self, name: str = "cos") -> None:
        super().__init__("cos", name)

    def _setup_attributes(self) -> None:
        self.input: ScalarAttribute = ScalarAttribute(f"{self.name}.input")
        self.output: ScalarAttribute = ScalarAttribute(f"{self.name}.output")


class CrossProductNode(Node):
    """Maya crossProduct node with enhanced interface."""

    def __init__(self, name: str = "crossProduct") -> None:
        super().__init__("crossProduct", name)

    def _setup_attributes(self) -> None:
        self.input1 = Vector3Attribute(f"{self.name}.input1")
        self.input2 = Vector3Attribute(f"{self.name}.input2")
        self.output = Vector3Attribute(f"{self.name}.output")


class CurveInfoNode(Node):
    """Maya curveInfo node with enhanced interface."""

    def __init__(self, name: str = "curveInfo") -> None:
        super().__init__("curveInfo", name)

    def _setup_attributes(self) -> None:
        self.input_curve = NurbsCurveAttribute(f"{self.name}.inputCurve")
        self.arc_length = ScalarAttribute(f"{self.name}.arcLength")
        self.control_points = IndexableScalarAttribute(f"{self.name}.controlPoints")
        self.knots = IndexableScalarAttribute(f"{self.name}.knots")
        self.weights = IndexableScalarAttribute(f"{self.name}.weights")


class DecomposeMatrixNode(Node):
    """Maya decomposeMatrix node with enhanced interface."""

    def __init__(self, name: str = "decomposeMatrix") -> None:
        super().__init__("decomposeMatrix", name)

    def _setup_attributes(self) -> None:
        self.input_matrix = MatrixAttribute(f"{self.name}.inputMatrix")
        self.input_rotate_order = RotateOrderAttribute(f"{self.name}.inputRotateOrder")
        self.output_quat = QuatAttribute(f"{self.name}.outputQuat")
        self.output_rotate = Vector3Attribute(f"{self.name}.outputRotate")
        self.output_scale = Vector3Attribute(f"{self.name}.outputScale")
        self.output_shear = Vector3Attribute(f"{self.name}.outputShear")
        self.output_translate = Vector3Attribute(f"{self.name}.outputTranslate")


class DistanceBetweenNode(Node):
    """Maya distanceBetween node with enhanced interface."""

    def __init__(self, name: str = "distanceBetween") -> None:
        super().__init__("distanceBetween", name)

    def _setup_attributes(self) -> None:
        self.point1 = Vector3Attribute(f"{self.name}.point1")
        self.point2 = Vector3Attribute(f"{self.name}.point2")
        self.input_matrix1 = MatrixAttribute(f"{self.name}.inMatrix1")
        self.input_matrix2 = MatrixAttribute(f"{self.name}.inMatrix2")
        self.distance = ScalarAttribute(f"{self.name}.distance")


class DivideNode(Node):
    """Maya divide node with enhanced interface."""

    def __init__(self, name: str = "divide") -> None:
        super().__init__("divide", name)

    def _setup_attributes(self) -> None:
        self.input1 = ScalarAttribute(f"{self.name}.input1")
        self.input2 = ScalarAttribute(f"{self.name}.input2")
        self.output = ScalarAttribute(f"{self.name}.output")


class EulerToQuatNode(Node):
    """Maya eulerToQuat node with enhanced interface."""

    def __init__(self, name: str = "eulerToQuat") -> None:
        super().__init__("eulerToQuat", name)

    def _setup_attributes(self) -> None:
        self.output_quat = QuatAttribute(f"{self.name}.outputQuat")
        self.input_rotate_order = EnumAttribute(f"{self.name}.inputRotateOrder")
        self.input_rotate = Vector3Attribute(f"{self.name}.inputRotate")


class FourByFourMatrixNode(Node):
    """Maya fourByFourMatrix node with enhanced interface."""

    def __init__(self, name: str = "fourByFourMatrix") -> None:
        super().__init__("fourByFourMatrix", name)

    def _setup_attributes(self) -> None:
        self.in_00 = ScalarAttribute(f"{self.name}.in00")
        self.in_01 = ScalarAttribute(f"{self.name}.in01")
        self.in_02 = ScalarAttribute(f"{self.name}.in02")
        self.in_03 = ScalarAttribute(f"{self.name}.in03")
        self.in_10 = ScalarAttribute(f"{self.name}.in10")
        self.in_11 = ScalarAttribute(f"{self.name}.in11")
        self.in_12 = ScalarAttribute(f"{self.name}.in12")
        self.in_13 = ScalarAttribute(f"{self.name}.in13")
        self.in_20 = ScalarAttribute(f"{self.name}.in20")
        self.in_21 = ScalarAttribute(f"{self.name}.in21")
        self.in_22 = ScalarAttribute(f"{self.name}.in22")
        self.in_23 = ScalarAttribute(f"{self.name}.in23")
        self.in_30 = ScalarAttribute(f"{self.name}.in30")
        self.in_31 = ScalarAttribute(f"{self.name}.in31")
        self.in_32 = ScalarAttribute(f"{self.name}.in32")
        self.in_33 = ScalarAttribute(f"{self.name}.in33")
        self.output = MatrixAttribute(f"{self.name}.output")


class InverseMatrixNode(Node):
    """Maya inverseMatrix node with enhanced interface."""

    def __init__(self, name: str = "inverseMatrix") -> None:
        super().__init__("inverseMatrix", name)

    def _setup_attributes(self) -> None:
        self.input_matrix = MatrixAttribute(f"{self.name}.inputMatrix")
        self.output_matrix = MatrixAttribute(f"{self.name}.outputMatrix")


class LengthNode(Node):
    """Maya length node with enhanced interface."""

    def __init__(self, name: str = "length") -> None:
        super().__init__("length", name)

    def _setup_attributes(self) -> None:
        self.input = Vector3Attribute(f"{self.name}.input")
        self.output = ScalarAttribute(f"{self.name}.output")


class LerpNode(Node):
    """Maya lerp node with enhanced interface."""

    def __init__(self, name: str = "lerp") -> None:
        super().__init__("lerp", name)

    def _setup_attributes(self) -> None:
        self.input1 = ScalarAttribute(f"{self.name}.input1")
        self.input2 = ScalarAttribute(f"{self.name}.input2")
        self.weight = ScalarAttribute(f"{self.name}.weight")
        self.output = ScalarAttribute(f"{self.name}.output")


class MotionPathNode(Node):
    """Maya motionPath node with enhanced interface."""

    def __init__(self, name: str = "motionPath") -> None:
        super().__init__("motionPath", name)

    def _setup_attributes(self) -> None:

        self.geometry_path = NurbsCurveAttribute(f"{self.name}.geometryPath")
        self.rotate_order = RotateOrderAttribute(f"{self.name}.rotateOrder")

        self.u_value = ScalarAttribute(f"{self.name}.uValue")
        self.fraction_mode = BooleanAttribute(f"{self.name}.fractionMode")

        self.follow = BooleanAttribute(f"{self.name}.follow")
        self.world_up_type = MotionPathWorldUpTypeAttribute(f"{self.name}.worldUpType")
        self.world_up_vector = Vector3Attribute(f"{self.name}.worldUpVector")
        self.world_up_matrix = MatrixAttribute(f"{self.name}.worldUpMatrix")
        self.inverse_up = BooleanAttribute(f"{self.name}.inverseUp")
        self.inverse_front = BooleanAttribute(f"{self.name}.inverseFront")
        self.front_axis = UnsignedAxisAttribute(f"{self.name}.frontAxis")
        self.up_axis = UnsignedAxisAttribute(f"{self.name}.upAxis")

        self.front_twist = ScalarAttribute(f"{self.name}.frontTwist")
        self.up_twist = ScalarAttribute(f"{self.name}.upTwist")
        self.side_twist = ScalarAttribute(f"{self.name}.sideTwist")

        self.bank = BooleanAttribute(f"{self.name}.bank")
        self.bank_limit = ScalarAttribute(f"{self.name}.bankLimit")
        self.bank_scale = ScalarAttribute(f"{self.name}.bankScale")
        self.bank_scale = ScalarAttribute(f"{self.name}.bankScale")

        self.all_coordinates = Vector3Attribute(f"{self.name}.allCoordinates")
        self.orient_matrix = MatrixAttribute(f"{self.name}.orientMatrix")
        self.rotate = Vector3Attribute(f"{self.name}.rotate")


class MultiplyNode(Node):
    """Maya multiply node with enhanced interface."""

    def __init__(self, name: str = "multiply") -> None:
        super().__init__("multiply", name)

    def _setup_attributes(self) -> None:
        self.input: IndexableScalarAttribute = IndexableScalarAttribute(f"{self.name}.input")
        self.output: ScalarAttribute = ScalarAttribute(f"{self.name}.output")


class MultiplyDivideNode(Node):
    """Maya multiplyDivide node with enhanced interface."""

    def __init__(self, name: str = "multiplyDivide") -> None:
        super().__init__("multiplyDivide", name)

    def _setup_attributes(self) -> None:
        self.input1 = Vector3Attribute(f"{self.name}.input1")
        self.input2 = Vector3Attribute(f"{self.name}.input2")
        self.operation = MultiplyDivideOperationAttribute(f"{self.name}.operation")
        self.output = Vector3Attribute(f"{self.name}.output")


class MultiplyPointByMatrixNode(Node):
    """Maya multiplyPointByMatrix node with enhanced interface."""

    def __init__(self, name: str = "multiplyPointByMatrix") -> None:
        super().__init__("multiplyPointByMatrix", name)

    def _setup_attributes(self) -> None:
        self.input_point = Vector3Attribute(f"{self.name}.input")
        self.input_matrix = MatrixAttribute(f"{self.name}.matrix")
        self.output = Vector3Attribute(f"{self.name}.output")


class MultiplyVectorByMatrixNode(Node):
    """Maya multiplyVectorByMatrix node with enhanced interface."""

    def __init__(self, name: str = "multiplyVectorByMatrix") -> None:
        super().__init__("multiplyVectorByMatrix", name)

    def _setup_attributes(self) -> None:
        self.input_vector = Vector3Attribute(f"{self.name}.input")
        self.input_matrix = MatrixAttribute(f"{self.name}.matrix")
        self.output = Vector3Attribute(f"{self.name}.output")


class MultMatrixNode(Node):
    """Maya multMatrix node with enhanced interface."""

    def __init__(self, name: str = "multMatrix") -> None:
        super().__init__("multMatrix", name)

    def _setup_attributes(self) -> None:
        self.matrix_in = IndexableMatrixAttribute(f"{self.name}.matrixIn")
        self.matrix_sum = MatrixAttribute(f"{self.name}.matrixSum")


class NormalizeNode(Node):
    """Maya normalize node with enhanced interface."""

    def __init__(self, name: str = "normalize") -> None:
        super().__init__("normalize", name)

    def _setup_attributes(self) -> None:
        self.input = Vector3Attribute(f"{self.name}.input")
        self.output = Vector3Attribute(f"{self.name}.output")


class QuatInvertNode(Node):
    """Maya quatInvert node with enhanced interface."""

    def __init__(self, name: str = "quatInvert") -> None:
        super().__init__("quatInvert", name)

    def _setup_attributes(self) -> None:
        self.input_quat = QuatAttribute(f"{self.name}.inputQuat")
        self.output_quat = QuatAttribute(f"{self.name}.outputQuat")


class QuatNormalizeNode(Node):
    """Maya quatNormalize node with enhanced interface."""

    def __init__(self, name: str = "quatNormalize") -> None:
        super().__init__("quatNormalize", name)

    def _setup_attributes(self) -> None:
        self.input_quat = QuatAttribute(f"{self.name}.inputQuat")
        self.output_quat = QuatAttribute(f"{self.name}.outputQuat")


class QuatProdNode(Node):
    """Maya quatProd node with enhanced interface."""

    def __init__(self, name: str = "quatProd") -> None:
        super().__init__("quatProd", name)

    def _setup_attributes(self) -> None:
        self.input1_quat = QuatAttribute(f"{self.name}.input1Quat")
        self.input2_quat = QuatAttribute(f"{self.name}.input2Quat")
        self.output_quat = QuatAttribute(f"{self.name}.outputQuat")


class QuatSlerpNode(Node):
    """Maya quatSlerp node with enhanced interface."""

    def __init__(self, name: str = "quatSlerp") -> None:
        super().__init__("quatSlerp", name)

    def _setup_attributes(self) -> None:
        self.input1_quat = QuatAttribute(f"{self.name}.input1Quat")
        self.input2_quat = QuatAttribute(f"{self.name}.input2Quat")
        self.input_t = ScalarAttribute(f"{self.name}.inputT")
        self.output_quat = QuatAttribute(f"{self.name}.outputQuat")


class QuatToEulerNode(Node):
    """Maya quatToEuler node with enhanced interface."""

    def __init__(self, name: str = "quatToEuler") -> None:
        super().__init__("quatToEuler", name)

    def _setup_attributes(self) -> None:
        self.input_quat = QuatAttribute(f"{self.name}.inputQuat")
        self.input_rotate_order = RotateOrderAttribute(f"{self.name}.inputRotateOrder")
        self.output_rotate = Vector3Attribute(f"{self.name}.outputRotate")


class PickMatrixNode(Node):
    """Maya pickMatrix node with enhanced interface."""

    def __init__(self, name: str = "pickMatrix") -> None:
        super().__init__("pickMatrix", name)

    def _setup_attributes(self) -> None:
        self.input_matrix = MatrixAttribute(f"{self.name}.inputMatrix")
        self.use_translate = BooleanAttribute(f"{self.name}.useTranslate")
        self.use_rotate = BooleanAttribute(f"{self.name}.useRotate")
        self.use_scale = BooleanAttribute(f"{self.name}.useScale")
        self.use_shear = BooleanAttribute(f"{self.name}.useShear")
        self.output_matrix = MatrixAttribute(f"{self.name}.outputMatrix")


class PlusMinusAverageNode(Node):
    """Maya plusMinusAverage node with enhanced interface."""

    def __init__(self, name: str = "plusMinusAverage") -> None:
        super().__init__("plusMinusAverage", name)

    def _setup_attributes(self) -> None:
        self.input_3d = IndexableVector3Attribute(f"{self.name}.input3D")
        self.input_2d = IndexableVector2Attribute(f"{self.name}.input3D")
        self.input_1d = IndexableScalarAttribute(f"{self.name}.input1D")
        self.output_3d = Vector3Attribute(f"{self.name}.output3D")
        self.output_2d = Vector2Attribute(f"{self.name}.output2D")
        self.output_1d = ScalarAttribute(f"{self.name}.output1D")
        self.operation = PlusMinusAverageOperationAttribute(f"{self.name}.operation")


class RemapValueNode(Node):
    """Maya remapValue node with enhanced interface."""

    def __init__(self, name: str = "remapValue") -> None:
        super().__init__("remapValue", name)

    def _setup_attributes(self) -> None:
        self.input_value = ScalarAttribute(f"{self.name}.inputValue")
        self.output = ScalarAttribute(f"{self.name}.output")
        self.input_max = ScalarAttribute(f"{self.name}.inputMax")
        self.input_min = ScalarAttribute(f"{self.name}.inputMin")
        self.output_max = ScalarAttribute(f"{self.name}.outputMax")
        self.output_min = ScalarAttribute(f"{self.name}.outputMin")


class RowFromMatrixNode(Node):
    """Maya rowFromMatrix node with enhanced interface."""

    def __init__(self, name: str = "rowFromMatrix") -> None:
        super().__init__("rowFromMatrix", name)

    def _setup_attributes(self) -> None:
        self.input = IntegerAttribute(f"{self.name}.input")
        self.matrix = MatrixAttribute(f"{self.name}.matrix")
        self.output = Vector4Attribute(f"{self.name}.output")


class SinNode(Node):
    """Maya sin node with enhanced interface."""

    def __init__(self, name: str = "sin") -> None:
        super().__init__("sin", name)

    def _setup_attributes(self) -> None:
        self.input: ScalarAttribute = ScalarAttribute(f"{self.name}.input")
        self.output: ScalarAttribute = ScalarAttribute(f"{self.name}.output")


class SubtractNode(Node):
    """Maya subtract node with enhanced interface."""

    def __init__(self, name: str = "subtract") -> None:
        super().__init__("subtract", name)

    def _setup_attributes(self) -> None:
        self.input1: ScalarAttribute = ScalarAttribute(f"{self.name}.input1")
        self.input2: ScalarAttribute = ScalarAttribute(f"{self.name}.input2")
        self.output: ScalarAttribute = ScalarAttribute(f"{self.name}.output")


class SumNode(Node):
    """Maya sum node with enhanced interface."""

    def __init__(self, name: str = "sum") -> None:
        super().__init__("sum", name)

    def _setup_attributes(self) -> None:
        self.input: IndexableScalarAttribute = IndexableScalarAttribute(f"{self.name}.input")
        self.output: ScalarAttribute = ScalarAttribute(f"{self.name}.output")


class UvPinNode(Node):
    """Maya uvPin node with enhanced interface."""

    def __init__(self, name: str = "uvPin") -> None:
        super().__init__("uvPin", name)

    def _setup_attributes(self) -> None:
        self.original_geometry = GeometryAttribute(f"{self.name}.originalGeometry")
        self.deformed_geometry = GeometryAttribute(f"{self.name}.deformedGeometry")

        self.normal_axis = AxisAttribute(f"{self.name}.normalAxis")
        self.tangent_axis = AxisAttribute(f"{self.name}.tangentAxis")
        self.uv_set_name = StringAttribute(f"{self.name}.uvSetName")
        self.normalized_isoparms = BooleanAttribute(f"{self.name}.normalizedIsoParms")
        self.normal_override = UvPinNormalOverrideAttribute(f"{self.name}.normalOverride")
        self.relative_space_mode = UvPinRelativeSpaceModeAttribute(f"{self.name}.relativeSpaceMode")
        self.relative_space_matrix = MatrixAttribute(f"{self.name}.relativeSpaceMatrix")
        self.coordinate = IndexableUvPinCoordinateAttribute(f"{self.name}.coordinate")

        self.output_matrix = IndexableMatrixAttribute(f"{self.name}.outputMatrix")
        self.output_translate = IndexableVector3Attribute(f"{self.name}.outputMatrix")


class WtAddMatrixNode(Node):
    """Maya wtAddMatrix node with enhanced interface."""

    def __init__(self, name: str = "wtAddMatrix") -> None:
        super().__init__("wtAddMatrix", name)

    def _setup_attributes(self) -> None:
        self.weight_matrix: IndexableWtMatrixAttribute = IndexableWtMatrixAttribute(
            f"{self.name}.wtMatrix"
        )
        self.matrix_sum: MatrixAttribute = MatrixAttribute(f"{self.name}.matrixSum")
