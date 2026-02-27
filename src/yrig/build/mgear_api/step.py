from dataclasses import dataclass


@dataclass
class BuildStep:
    name: str
    weight: float = 1
