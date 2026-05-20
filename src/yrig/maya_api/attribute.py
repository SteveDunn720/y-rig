from __future__ import annotations

from abc import abstractmethod
from enum import IntEnum
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Iterable,
    Iterator,
    Self,
    Sequence,
    TypeAlias,
    TypeVar,
)

import maya.cmds as cmds
from maya.api.OpenMaya import MMatrix

from yrig.maya_api.enum import (
    Axis,
    ConditionOperation,
    MotionPathWorldUpType,
    MultiplyDivideOperation,
    PlusMinusAverageOperation,
    RotateOrder,
    UnsignedAxis,
    UvPinNormalOverride,
    UvPinRelativeSpaceMode,
)

if TYPE_CHECKING:
    from yrig.maya_api.node import Node

AttributeType = TypeVar("AttributeType", bound="Attribute")

EnumType = TypeVar("EnumType", bound=IntEnum)

# fmt: off
MatrixTuple: TypeAlias = tuple[
    float, float, float, float,
    float, float, float, float,
    float, float, float, float,
    float, float, float, float,
]
# fmt: on

T = TypeVar("T")


def _compact_kwargs(dict: dict[str, Any | None]) -> dict[str, Any]:
    return {key: value for key, value in dict.items() if value is not None}


class Attribute(Generic[T]):
    """Base class for all Maya attributes."""

    def __init__(self, attr_path: str) -> None:
        self.attr_path = attr_path

    def __str__(self) -> str:
        """Return the attribute path when used as a string."""
        return self.attr_path

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.attr_path}')"

    def get(self) -> T:
        """Get the value of this attribute."""
        return cmds.getAttr(self.attr_path)

    def set(self, value: T) -> None:
        """Set the value of this attribute."""
        cmds.setAttr(self.attr_path, value)  # type: ignore

    @property
    def value(self) -> T:
        """Get the value of this attribute."""
        return self.get()

    @value.setter
    def value(self, val: T) -> None:
        """Set the value of this attribute."""
        self.set(val)

    def connect_from(self, source_attr: str | Attribute) -> None:
        """Connect another attribute to this one."""
        source = str(source_attr)  # Works with both strings and Attribute objects
        cmds.connectAttr(source, self.attr_path)

    def connect_to(self, dest_attr: str | Attribute) -> None:
        """Connect this attribute to another one."""
        dest = str(dest_attr)
        cmds.connectAttr(self.attr_path, dest)

    def exists(self) -> bool:
        """Check if this attribute exists."""
        return cmds.objExists(self.attr_path)

    def set_locked(self, locked: bool) -> None:
        """Lock or unlock this attribute."""
        cmds.setAttr(self.attr_path, lock=locked)

    def set_keyable(self, keyable: bool) -> None:
        """Set this attribute as keyable or not."""
        cmds.setAttr(self.attr_path, keyable=keyable)

    def set_channel_box(self, enabled: bool) -> None:
        """Control whether this attribute is displayed in the channel box."""
        cmds.setAttr(self.attr_path, channelBox=enabled)


class StringAttribute(Attribute[str]):
    """Maya string attribute."""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

    def get(self) -> str:
        """Get the value of this attribute."""
        return cmds.getAttr(self.attr_path)

    def set(self, value: str) -> None:
        """Set the value of this attribute."""
        cmds.setAttr(self.attr_path, value, type="string")


class NumericAttribute(Attribute[T]):
    """Base class for numeric Maya attributes (int/float-like values)."""

    pass


class ScalarAttribute(NumericAttribute[float]):
    """Single float (double) Maya attribute."""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

    @classmethod
    def create(
        cls,
        node: Node | str,
        name: str,
        nice_name: str | None = None,
        short_name: str | None = None,
        default: float | None = None,
        keyable: bool = True,
        channel_box: bool = True,
        min: float | None = None,
        max: float | None = None,
        soft_min: float | None = None,
        soft_max: float | None = None,
    ) -> Self:
        node_name = str(node)
        kwargs = _compact_kwargs(
            {
                "longName": name,
                "niceName": nice_name,
                "shortName": short_name,
                "defaultValue": default,
                "keyable": keyable,
                "minValue": min,
                "maxValue": max,
                "softMinValue": soft_min,
                "softMaxValue": soft_max,
            }
        )
        cmds.addAttr(node_name, **kwargs)
        attribute = cls(f"{node_name}.{name}")
        if not keyable:
            attribute.set_channel_box(channel_box)
        return attribute


class IntegerAttribute(NumericAttribute[int]):
    """Single integer Maya attribute."""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

    def get(self) -> int:
        """Get the value of this attribute."""
        return int(cmds.getAttr(self.attr_path))

    def set(self, value: float | int) -> None:
        """Set the value of this attribute."""
        cmds.setAttr(self.attr_path, int(value))  # type: ignore


class BooleanAttribute(Attribute[bool]):
    """A Maya attribute of a bool type."""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

    def get(self) -> bool:
        """Get the value of this attribute."""
        return bool(cmds.getAttr(self.attr_path))

    def set(self, value: bool) -> None:
        """Set the value of this attribute."""
        cmds.setAttr(self.attr_path, 1 if value else 0)  # type: ignore


class MatrixAttribute(Attribute[MMatrix]):
    """A Maya attribute of the matrix type."""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

    def get(self) -> MMatrix:
        """Get the value of this attribute."""
        return_list = cmds.getAttr(self.attr_path)
        matrix = MMatrix(return_list)
        return matrix

    def set(self, value: MatrixTuple | Sequence[float] | MMatrix) -> None:
        """Set the value of this attribute."""
        if isinstance(value, MMatrix):
            cmds.setAttr(self.attr_path, tuple(value), type="matrix")  # type: ignore
        if len(value) != 16:
            raise ValueError(
                f"{value} is not a valid matrix input, it should be a Sequence of 16 floats or a MMatrix"
            )
        cmds.setAttr(self.attr_path, tuple(value), type="matrix")  # type: ignore


class GeometryAttribute(Attribute):
    """A Maya attribute of the geometry type."""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)


class NurbsCurveAttribute(GeometryAttribute):
    """A Maya attribute of the nurbsCurve type."""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)


class Vector2Attribute(Attribute[tuple[float, float]]):
    """A Maya attribute of the type double2 (XY)"""

    def __init__(self, attr_path: str):
        super().__init__(attr_path)

        self.x = ScalarAttribute(f"{attr_path}X")
        self.y = ScalarAttribute(f"{attr_path}Y")

    def get(self) -> tuple[float, float]:
        """Get the value of this attribute."""
        return_list = cmds.getAttr(self.attr_path)
        tuple = return_list[0]
        return tuple

    def set(self, value: tuple[float, float]) -> None:
        """Set the value of this attribute."""
        cmds.setAttr(self.attr_path, *value)  # type: ignore


class NurbsSurfaceAttribute(GeometryAttribute):
    """A Maya attribute of the nurbsSurface type."""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)


class Vector3Attribute(Attribute[tuple[float, float, float]]):
    """A Maya attribute of the type double3 (XYZ)"""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

        self.x = ScalarAttribute(f"{attr_path}X")
        self.y = ScalarAttribute(f"{attr_path}Y")
        self.z = ScalarAttribute(f"{attr_path}Z")

    def get(self) -> tuple[float, float, float]:
        """Get the value of this attribute."""
        return_list = cmds.getAttr(self.attr_path)
        tuple = return_list[0]
        return tuple

    def set(self, value: tuple[float, float, float]) -> None:
        """Set the value of this attribute."""
        cmds.setAttr(self.attr_path, *value)  # type: ignore


class Vector4Attribute(Attribute[tuple[float, float, float]]):
    """A Maya attribute of the type double4 (XYZW)"""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

        self.x = ScalarAttribute(f"{attr_path}X")
        self.y = ScalarAttribute(f"{attr_path}Y")
        self.z = ScalarAttribute(f"{attr_path}Z")
        self.w = ScalarAttribute(f"{attr_path}W")


class ColorAttribute(Attribute[tuple[float, float, float]]):
    """A Maya attribute of the type color (RGB)"""

    def __init__(self, attr_path: str):
        super().__init__(attr_path)

        self.r = ScalarAttribute(f"{attr_path}R")
        self.g = ScalarAttribute(f"{attr_path}G")
        self.b = ScalarAttribute(f"{attr_path}B")

    def get(self) -> tuple[float, float, float]:
        """Get the value of this attribute."""
        return_list = cmds.getAttr(self.attr_path)
        tuple = return_list[0]
        return tuple

    def set(self, value: tuple[float, float, float]) -> None:
        """Set the value of this attribute."""
        cmds.setAttr(self.attr_path, *value)  # type: ignore


class QuatAttribute(Attribute[tuple[float, float, float]]):
    """A Maya attribute of the compound Quaternion type (XYZW)"""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

        self.x = ScalarAttribute(f"{attr_path}X")
        self.y = ScalarAttribute(f"{attr_path}Y")
        self.z = ScalarAttribute(f"{attr_path}Z")
        self.w = ScalarAttribute(f"{attr_path}W")


class EnumAttribute(Attribute[EnumType], Generic[EnumType]):
    """A Maya attribute of the enum type."""

    enum_type: type[EnumType]

    def get(self) -> EnumType:
        return self.enum_type(cmds.getAttr(self.attr_path))

    def set(self, value: EnumType | int) -> None:
        cmds.setAttr(self.attr_path, int(value))  # type: ignore


class RotateOrderAttribute(EnumAttribute[RotateOrder]):
    enum_type = RotateOrder


class AxisAttribute(EnumAttribute[Axis]):
    enum_type = Axis


class UnsignedAxisAttribute(EnumAttribute[UnsignedAxis]):
    enum_type = UnsignedAxis


class MotionPathWorldUpTypeAttribute(EnumAttribute[MotionPathWorldUpType]):
    enum_type = MotionPathWorldUpType


class MultiplyDivideOperationAttribute(EnumAttribute[MultiplyDivideOperation]):
    enum_type = MultiplyDivideOperation


class UvPinNormalOverrideAttribute(EnumAttribute[UvPinNormalOverride]):
    enum_type = UvPinNormalOverride


class UvPinRelativeSpaceModeAttribute(EnumAttribute[UvPinRelativeSpaceMode]):
    enum_type = UvPinRelativeSpaceMode


class ConditionOperationAttribute(EnumAttribute[ConditionOperation]):
    enum_type = ConditionOperation


class PlusMinusAverageOperationAttribute(EnumAttribute[PlusMinusAverageOperation]):
    enum_type = PlusMinusAverageOperation


class IndexableAttribute(Attribute, Generic[AttributeType], Iterable[AttributeType]):
    """Base class for array-style Maya attributes supporting indexed access."""

    @abstractmethod
    def __getitem__(self, index: int) -> AttributeType:
        """Return the indexed attribute path: attr.input[0], attr.input[1], etc."""

    def __len__(self) -> int:
        """Get the number of elements in this array."""
        return cmds.getAttr(self.attr_path, size=True)

    def get_indices(self) -> list[int]:
        """Get all existing indices in this array."""
        return cmds.getAttr(self.attr_path, multiIndices=True) or []

    def __iter__(self) -> Iterator[AttributeType]:
        """Iterate over all existing, non-sparse elements in the array."""
        # This allows for loop iteration: for item in my_attr:
        for index in self.get_indices():
            yield self[index]


class IndexableScalarAttribute(IndexableAttribute[ScalarAttribute]):
    """A Maya attribute that supports indexing matrix attributes with bracket notation."""

    def __getitem__(self, index: int) -> ScalarAttribute:
        """Return the indexed attribute path: attr.input[0], attr.input[1], etc."""
        return ScalarAttribute(attr_path=f"{self.attr_path}[{index}]")


class IndexableVector2Attribute(IndexableAttribute[Vector2Attribute]):
    """A Maya attribute that supports indexing Vector3 attributes with bracket notation."""

    def __getitem__(self, index: int) -> Vector2Attribute:
        """Return the indexed attribute path: attr.input[0], attr.input[1], etc."""
        return Vector2Attribute(attr_path=f"{self.attr_path}[{index}]")


class IndexableVector3Attribute(IndexableAttribute[Vector3Attribute]):
    """A Maya attribute that supports indexing vector3 elements with bracket notation."""

    def __getitem__(self, index: int) -> Vector3Attribute:
        """Return the indexed attribute path: attr.input[0], attr.input[1], etc."""
        return Vector3Attribute(attr_path=f"{self.attr_path}[{index}]")


class IndexableMatrixAttribute(IndexableAttribute[MatrixAttribute]):
    """A Maya attribute that supports indexing matrix attributes with bracket notation."""

    def __getitem__(self, index: int) -> MatrixAttribute:
        """Return the indexed attribute path: attr.input[0], attr.input[1], etc."""
        return MatrixAttribute(attr_path=f"{self.attr_path}[{index}]")


class BlendMatrixTargetAttribute(Attribute):
    """A Maya attribute of the same compound type as the targets in a blendMatrix node."""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

        self.target_matrix = MatrixAttribute(f"{attr_path}.targetMatrix")
        self.use_matrix = BooleanAttribute(f"{attr_path}.useMatrix")
        self.weight = ScalarAttribute(f"{attr_path}.weight")
        self.scale_weight = ScalarAttribute(f"{attr_path}.scaleWeight")
        self.translate_weight = ScalarAttribute(f"{attr_path}.translateWeight")
        self.rotate_weight = ScalarAttribute(f"{attr_path}.rotateWeight")
        self.shear_weight = ScalarAttribute(f"{attr_path}.shearWeight")


class IndexableBlendMatrixTargetAttribute(IndexableAttribute[BlendMatrixTargetAttribute]):
    """A Maya attribute that supports indexing targets in a blendMatrix with bracket notation."""

    def __getitem__(self, index: int) -> BlendMatrixTargetAttribute:
        """Return the indexed attribute path: attr.input[0], attr.input[1], etc."""
        return BlendMatrixTargetAttribute(attr_path=f"{self.attr_path}[{index}]")


class WtMatrixAttribute(Attribute):
    """A Maya attribute of the same compound type as the wtMatrix elements in a wtAddMatrix node."""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

        self.matrix_in = MatrixAttribute(f"{attr_path}.matrixIn")
        self.weight_in = ScalarAttribute(f"{attr_path}.weightIn")


class IndexableWtMatrixAttribute(IndexableAttribute[WtMatrixAttribute]):
    """A Maya attribute that supports indexing elements in a wtAddMatrix with bracket notation."""

    def __getitem__(self, index: int) -> WtMatrixAttribute:
        """Return the indexed attribute path: attr.input[0], attr.input[1], etc."""
        return WtMatrixAttribute(attr_path=f"{self.attr_path}[{index}]")


class AimMatrixAxisAttribute(Attribute):
    """A Maya attribute of the same compound type as the aimMatrix axes."""

    def __init__(self, attr_path: str, axis_name: str) -> None:
        super().__init__(attr_path)

        self.input_axis = Vector3Attribute(f"{attr_path}.{axis_name}InputAxis")
        self.mode = EnumAttribute(f"{attr_path}.{axis_name}Mode")
        self.target_vector = Vector3Attribute(f"{attr_path}.{axis_name}TargetVector")
        self.target_matrix = MatrixAttribute(f"{attr_path}.{axis_name}TargetMatrix")


class UvPinCoordinateAttribute(Attribute[tuple[float, float]]):
    """A Maya attribute of the type UV"""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

        self.u = ScalarAttribute(f"{attr_path}.coordinateU")
        self.v = ScalarAttribute(f"{attr_path}.coordinateV")

    def get(self) -> tuple[float, float]:
        """Get the value of this attribute."""
        return_list = cmds.getAttr(self.attr_path)
        tuple = return_list[0]
        return tuple

    def set(self, value: tuple[float, float]) -> None:
        """Set the value of this attribute."""
        cmds.setAttr(self.attr_path, *value)  # type: ignore


class IndexableUvPinCoordinateAttribute(IndexableAttribute[UvPinCoordinateAttribute]):
    """A Maya attribute that supports indexing UV elements with bracket notation."""

    def __getitem__(self, index: int) -> UvPinCoordinateAttribute:
        """Return the indexed attribute path: attr.input[0], attr.input[1], etc."""
        return UvPinCoordinateAttribute(attr_path=f"{self.attr_path}[{index}]")


class ClosestPointOnSurfaceResultAttribute(Attribute):
    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

        self.position = Vector3Attribute(f"{attr_path}.position")
        self.parameter_u = ScalarAttribute(f"{attr_path}.parameterU")
        self.parameter_v = ScalarAttribute(f"{attr_path}.parameterV")


class MessageAttribute(Attribute):
    """A Maya message attribute."""

    def __init__(self, attr_path: str) -> None:
        super().__init__(attr_path)

    def connected_nodes(
        self,
        source: bool = True,
        destination: bool = False,
    ) -> list[str]:
        if not cmds.objExists(self.attr_path):
            return []
        return cmds.listConnections(self.attr_path, source=source, destination=destination)

    @property
    def source_node(self) -> str | None:
        source_nodes = self.connected_nodes(source=True, destination=False)
        source_node = source_nodes[0] if source_nodes else None
        return source_node

    @property
    def destination_nodes(self) -> list[str]:
        return self.connected_nodes(source=False, destination=True)


class IndexableMessageAttribute(IndexableAttribute[MessageAttribute]):
    """A Maya attribute that supports indexing message attributes with bracket notation."""

    def __getitem__(self, index: int) -> MessageAttribute:
        """Return the indexed attribute path: attr.input[0], attr.input[1], etc."""
        return MessageAttribute(attr_path=f"{self.attr_path}[{index}]")
