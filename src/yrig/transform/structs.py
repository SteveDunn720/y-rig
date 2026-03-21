from enum import Enum
from typing import Literal

Axis = Literal["x", "y", "z"]
Direction = Literal["x", "y", "z", "-x", "-y", "-z"]


class RotationOrder(Enum):
    """Enum for Maya rotation orders."""

    XYZ = 0
    YZX = 1
    ZXY = 2
    XZY = 3
    YXZ = 4
    ZYX = 5

    def __str__(self) -> str:
        return self.name
