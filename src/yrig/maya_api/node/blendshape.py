from yrig.maya_api.attribute import (
    ArrayAttribute,
    BlendShapeInbetweenInfoAttribute,
    BlendShapeInputAttribute,
    BlendShapeInputTargetAttribute,
    BlendShapeTargetDirectoryAttribute,
    BlendShapeWeightFunctionDataAttribute,
    BlendShapeWeightListAttribute,
    BooleanAttribute,
    DoubleArrayAttribute,
    EnumAttribute,
    GeometryAttribute,
    IntegerAttribute,
    Long3Attribute,
    ScalarAttribute,
    StringAttribute,
    UInt64ArrayAttribute,
    Vector3Attribute,
)
from yrig.maya_api.enum import BlendShapeDeformationOrder, BlendShapeOrigin

from .core import Node


class BlendShape(Node):
    """Maya blendShape node with enhanced interface."""

    node_type = "blendShape"

    def __init__(self, name: str = "blendShape") -> None:
        super().__init__(name)

    def _setup_attributes(self) -> None:
        self.base_origin = Vector3Attribute(f"{self.name}.baseOrigin")
        self.block_gpu = BooleanAttribute(f"{self.name}.blockGPU")
        self.deformation_order = EnumAttribute(
            f"{self.name}.deformationOrder", BlendShapeDeformationOrder
        )
        self.envelope = ScalarAttribute(f"{self.name}.envelope")
        self.inbetween_info_group = ArrayAttribute(
            f"{self.name}.inbetweenInfoGroup", BlendShapeInbetweenInfoAttribute
        )
        self.input = ArrayAttribute(f"{self.name}.input", BlendShapeInputAttribute)
        self.input_target = ArrayAttribute(
            f"{self.name}.inputTarget", BlendShapeInputTargetAttribute
        )
        self.local_vertex_frame = BooleanAttribute(f"{self.name}.localVertexFrame")
        self.map_64_bit_indices = UInt64ArrayAttribute(f"{self.name}.map64BitIndices")
        self.mid_layer_parent = IntegerAttribute(f"{self.name}.midLayerParent")
        self.offset_deformer = Vector3Attribute(f"{self.name}.offsetDeformer")
        self.origin = EnumAttribute(f"{self.name}.origin", BlendShapeOrigin)
        self.original_geometry = ArrayAttribute(f"{self.name}.originalGeometry", GeometryAttribute)
        self.paint_weights = DoubleArrayAttribute(f"{self.name}.paintWeights")
        self.target_directory = ArrayAttribute(
            f"{self.name}.targetDirectory", BlendShapeTargetDirectoryAttribute
        )
        self.target_origin = Vector3Attribute(f"{self.name}.targetOrigin")
        self.topology_check = BooleanAttribute(f"{self.name}.topologyCheck")
        self.weight = ArrayAttribute(f"{self.name}.weight", ScalarAttribute)
        self.weight_function = ArrayAttribute(
            f"{self.name}.weightFunction", BlendShapeWeightFunctionDataAttribute
        )
        self.weight_list = ArrayAttribute(f"{self.name}.weightList", BlendShapeWeightListAttribute)
        self.function = Long3Attribute(f"{self.name}.function")
        self.icon = ArrayAttribute(f"{self.name}.icon", StringAttribute)
