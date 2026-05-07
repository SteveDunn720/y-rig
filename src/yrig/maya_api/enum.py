from enum import IntEnum


class RotateOrder(IntEnum):
    XYZ = 0
    YZX = 1
    ZXY = 2
    XZY = 3
    YXZ = 4
    ZYX = 5


class Axis(IntEnum):
    X = 0
    Y = 1
    Z = 2
    NEG_X = 3
    NEG_Y = 4
    NEG_Z = 5


class UnsignedAxis(IntEnum):
    X = 0
    Y = 1
    Z = 2


class MotionPathWorldUpType(IntEnum):
    SCENE_UP = 0
    OBJECT_UP = 1
    OBJECT_ROTATION_UP = 2
    VECTOR = 3
    NORMAL = 4


class MultiplyDivideOperation(IntEnum):
    NO_OPERATION = 0
    MULTIPLY = 1
    DIVIDE = 2
    POWER = 3


class UvPinNormalOverride(IntEnum):
    AUTO = 0
    RAIL_CURVE = 1


class UvPinRelativeSpaceMode(IntEnum):
    WORLD = 0
    LOCAL = 1
    CUSTOM = 2
