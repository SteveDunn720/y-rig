from __future__ import annotations

from dataclasses import dataclass

from yrig.maya_api.enum import (
    PoseInterpolatorInterpolation,
    PoseInterpolatorPoseControllerDataItemType,
    PoseInterpolatorPoseType,
    RotateOrder,
    UnsignedAxis,
)


@dataclass
class PoseInterpolatorControllerDataItem:
    name: str
    type: PoseInterpolatorPoseControllerDataItemType
    value: bool | str | int | float


@dataclass
class PoseInterpolatorPoseControllerData:
    items: dict[int, PoseInterpolatorControllerDataItem]


@dataclass
class PoseInterpolatorPoseData:
    name: str
    rotations: list[tuple[float, float, float]]
    translations: list[tuple[float, float, float]]
    independent: bool
    rotation_falloff: float
    translation_falloff: float
    pose_type: PoseInterpolatorPoseType
    gaussian_falloff: float
    is_enabled: bool
    controller_data: dict[int, PoseInterpolatorPoseControllerData]


@dataclass
class PoseInterpolatorDriverData:
    matrix: str
    orient: tuple[float, float, float]
    rotate_axis: tuple[float, float, float]
    twist_axis: UnsignedAxis
    rotate_order: RotateOrder
    euler_twist: bool
    controllers: dict[int, str]


@dataclass
class PoseInterpolatorData:
    name: str
    allow_negative_weights: bool
    enable_rotation: bool
    enable_translation: bool
    interpolation: PoseInterpolatorInterpolation
    output_smoothing: float
    regularization: float
    drivers: list[PoseInterpolatorDriverData]
    poses: list[PoseInterpolatorPoseData]
    outputs: list[list[str]]
