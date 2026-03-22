from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from maya import cmds
from maya.api.OpenMaya import (
    MDoubleArray,
    MFnNurbsCurve,
    MPointArray,
    MSelectionList,
    MSpace,
)

from yrig.transform import get_shapes

log = logging.getLogger(__name__)

SHAPE_LIBRARY_DIR = Path(Path(__file__).resolve().parent / "shape_library")
_control_shape_data_cache: dict[ControlShape, ControlShapeData] = {}


class ControlShape(Enum):
    """Enum for available control shapes with file names."""

    CIRCLE = "circle"
    SQUARE = "square"
    ROUND_SQUARE = "round_square"
    CUBE = "cube"
    SPHERE = "sphere"
    LOCATOR = "locator"
    DIAMOND = "diamond"
    TRIANGLE = "triangle"
    HEXAGON = "hexagon"

    @property
    def filename(self) -> str:
        """returns the filename of the json file representing the control shape."""
        return self.value


@dataclass(frozen=True)
class NurbsCurveData:
    degree: int
    form: int
    cv_positions: list[tuple[float, float, float]]
    cv_weights: list[float]
    cv_positions: list[tuple[float, float, float]]
    cv_weights: list[float]
    knots: list[float]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "NurbsCurveData":
        return cls(
            degree=data["degree"],
            form=data["form"],
            cv_positions=[tuple(p) for p in data["cv_positions"]],
            cv_weights=data["cv_weights"],
            knots=data["knots"],
        )


@dataclass(frozen=True)
class NamedNurbsCurveData:
    name: str
    curve: NurbsCurveData


@dataclass(frozen=True)
class ControlShapeData:
    curves: list[NamedNurbsCurveData]

    def to_dict(self) -> dict:
        return {curve.name: curve.curve.to_dict() for curve in self.curves}

    @classmethod
    def from_dict(cls, data: dict) -> "ControlShapeData":
        return cls(
            curves=[
                NamedNurbsCurveData(name, NurbsCurveData.from_dict(curve_data))
                for name, curve_data in data.items()
            ]
        )


def get_cv_positions(curve_shape: str) -> list[tuple[float, float, float]]:
    """
    Gets the positions of all CVs for a given curve shape.
    Args:
        curve_shape(str): Name of curve shape node.
    Returns:
        list: A list of CV positions as tuples
    """
    sel: MSelectionList = MSelectionList()
    sel.add(curve_shape)
    curve_obj = sel.getDependNode(0)
    fn_curve: MFnNurbsCurve = MFnNurbsCurve(curve_obj)

    cv_positions: MPointArray = fn_curve.cvPositions(space=MSpace.kObject)
    positions: list[tuple[float, float, float]] = [
        (point.x, point.y, point.z) for point in cv_positions
    ]
    return positions


def get_cv_weights(curve_shape: str) -> list[float]:
    """
    Gets the weights of all CVs for a given curve shape.
    Args:
        curve_shape(str): Name of curve shape node.
    Returns:
        list: A list of CV weight values.
    """
    sel: MSelectionList = MSelectionList()
    sel.add(curve_shape)
    curve_obj = sel.getDependNode(0)
    fn_curve: MFnNurbsCurve = MFnNurbsCurve(curve_obj)

    cv_positions: MPointArray = fn_curve.cvPositions(space=MSpace.kObject)
    weights: list[float] = [point.w for point in cv_positions]
    return weights


def get_cv_data(curve_shape: str) -> tuple[list[tuple[float, float, float]], list[float]]:
    """
    Gets both the positions and weights of all CVs for a given curve shape.
    Args:
        curve_shape (str): Name of curve shape node.
    Returns:
        tuple: (positions, weights)
            positions (list[tuple[float, float, float]]): List of CV positions
            weights (list[float]): List of CV weights
    """
    sel: MSelectionList = MSelectionList()
    sel.add(curve_shape)
    curve_obj = sel.getDependNode(0)
    fn_curve: MFnNurbsCurve = MFnNurbsCurve(curve_obj)

    cv_positions: MPointArray = fn_curve.cvPositions(space=MSpace.kObject)
    positions: list[tuple[float, float, float]] = [
        (point.x, point.y, point.z) for point in cv_positions
    ]
    weights: list[float] = [point.w for point in cv_positions]

    return positions, weights


def get_knots(curve_shape: str) -> list[float]:
    """
    Gets the knot vector for a given curve shape.
    Args:
        curve_shape(str): Name of curve shape node.
    Returns:
        list: A list of knot values. (aka knot vector)
    """
    sel: MSelectionList = MSelectionList()
    sel.add(curve_shape)
    curve_obj = sel.getDependNode(0)
    fn_curve: MFnNurbsCurve = MFnNurbsCurve(curve_obj)

    knots_array: MDoubleArray = fn_curve.knots()
    knots: list[float] = [knot for knot in knots_array]
    return knots


def get_control_shape_data(curve: str) -> ControlShapeData:
    curves: list[NamedNurbsCurveData] = []
    for curve in get_shapes(transform=curve):
        degree: int = cmds.getAttr(curve + ".degree")
        form: int = cmds.getAttr(curve + ".form")
        cv_positions: list[tuple[float, float, float]]
        cv_weights: list[float]
        cv_positions, cv_weights = get_cv_data(curve_shape=curve)
        knots: list[float] = get_knots(curve_shape=curve)
        curve_data = NurbsCurveData(degree, form, cv_positions, cv_weights, knots)
        curves.append(NamedNurbsCurveData(curve, curve_data))
    return ControlShapeData(curves)


def control_shape_data_to_json(data: ControlShapeData) -> str:
    return json.dumps(data.to_dict(), indent=2)


def control_shape_from_json(json_str: str) -> ControlShapeData:
    data = json.loads(json_str)
    return ControlShapeData.from_dict(data)


def get_curve_data(curve_shape: ControlShape | str) -> ControlShapeData:
    """
    Args:
        curve_shape(ControlShape): Name of the control shape to retrieve.
    Returns:
        dict: Curve data.
    """
    if isinstance(curve_shape, str):
        curve_shape: ControlShape = ControlShape[curve_shape.strip().upper()]
    if curve_shape not in _control_shape_data_cache:
        # check if curve dict is a file and convert it to dictionary if it is
        file_path: Path = SHAPE_LIBRARY_DIR / f"{curve_shape.filename}.json"
        if not file_path.exists():
            raise RuntimeError(
                f"The shape file for {curve_shape.filename} couldn't be found in the shape library. "
                f"You must write out the file {file_path} before reading."
            )

        with open(file_path, "r") as json_file:
            json_data = json_file.read()
            _control_shape_data_cache[curve_shape] = control_shape_from_json(json_data)
    return _control_shape_data_cache[curve_shape]


def write_curve_to_library(curve: str | None = None, name: str | None = None, force: bool = False):
    """
    Saves selected or defined curve to shape library.

    Args:
        control(str): Name of control to save. If None, uses the current selection.
        name(str): Name of the json file to save. If None, uses the chosen control.
    Returns:
        list: A list of CV weight values.
    """
    # make sure we either define a curve or have one selected
    # also make sure we're using the transform node
    if not curve:
        selection: list[str] = cmds.ls(selection=True)
        if len(selection) == 0:
            raise RuntimeError(
                "Unable to write control shape to file, no control transform was defined, and no control is selected."
            )
        curve: str = selection[0]

    # if a name is not defined, use the curves name instead
    if not name:
        name: str = curve

    json_path: Path = SHAPE_LIBRARY_DIR / f"{name}.json"
    if json_path.exists():
        if force:
            pass
        else:
            confirm: str = cmds.confirmDialog(
                title="File Overwrite",
                message=f"{json_path} already exists and will be overwritten, are you sure you want to write the file?",
                button=["Yes", "No"],
                defaultButton="Yes",
                cancelButton="No",
                dismissString="No",
            )
            if confirm == "Yes":
                pass
            else:
                return

    # get curve data
    curve_data = get_control_shape_data(curve=curve)
    json_dump = control_shape_data_to_json(curve_data)
    with open(file=json_path, mode="w") as json_file:
        json_file.write(json_dump)
