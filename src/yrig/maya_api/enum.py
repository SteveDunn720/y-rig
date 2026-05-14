from enum import IntEnum


class RotateOrder(IntEnum):
    XYZ = 0
    YZX = 1
    ZXY = 2
    XZY = 3
    YXZ = 4
    ZYX = 5

    def __str__(self) -> str:
        return self.name


class Axis(IntEnum):
    X = 0
    Y = 1
    Z = 2
    NEG_X = 3
    NEG_Y = 4
    NEG_Z = 5

    @classmethod
    def from_str(cls, value: str) -> "Axis":
        match value.lower():
            case "x":
                return cls.X
            case "y":
                return cls.Y
            case "z":
                return cls.Z
            case "-x":
                return cls.NEG_X
            case "-y":
                return cls.NEG_Y
            case "-z":
                return cls.NEG_Z
            case _:
                raise ValueError(f"{value} is not a valid Axis. It should be x,y,z or -x,-y,-z.")


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


class ConditionOperation(IntEnum):
    EQUAL = 0
    NOT_EQUAL = 1
    GREATER_THAN = 2
    GREATER_OR_EQUAL = 3
    LESS_THAN = 4
    LESS_OR_EQUAL = 5


class PlusMinusAverageOperation(IntEnum):
    NO_OPERATION = 0
    SUM = 1
    SUBTRACT = 2
    AVERAGE = 3
