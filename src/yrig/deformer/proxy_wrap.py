# type:ignore
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from maya import cmds


@dataclass
class ProximityWrap:
    node: str
    drivers: list[str] = field(default_factory=list)
    driven: list[str] = field(default_factory=list)

    falloff_scale: float = 1.0
    dropoff_rate_scale: float = 1.0
    smooth_influences: int = 0
    smooth_normals: int = 0
    span_samples: int = 1
    wrap_mode: int = 0
    max_drivers: int = 0

    @classmethod
    def create(
        cls,
        drivers: str | list[str],
        driven: str | list[str],
        name: str | None = None,
        falloff_scale: float | None = None,
        dropoff_rate_scale: float | None = None,
        smooth_influences: int | None = None,
        smooth_normals: int | None = None,
        span_samples: int | None = None,
        wrap_mode: int | None = None,
        max_drivers: int | None = None,
    ) -> ProximityWrap:
        """Create and return a proximity-wrap representation.

        Args:
            drivers:
                Driver mesh transform or list of driver mesh transforms.

            driven:
                Driven mesh transform or list of driven mesh transforms.

            name:
                Optional proximityWrap node name.

            falloff_scale:
                Global multiplier applied to the driver falloff range.

            dropoff_rate_scale:
                Global multiplier applied to the inverse-distance dropoff.

            smooth_influences:
                Number of influence-smoothing iterations.

            smooth_normals:
                Number of normal-smoothing iterations.

            span_samples:
                Number of samples used for span-based calculations.

            wrap_mode:
                Maya proximity-wrap mode enum value.

            max_drivers:
                Maximum drivers considered for each driven point.

        Returns:
            The created ProximityWrap dataclass.
        """
        driver_list = _as_list(drivers)
        driven_list = _as_list(driven)

        if not driver_list:
            raise ValueError("At least one driver mesh is required.")

        if not driven_list:
            raise ValueError("At least one driven mesh is required.")

        driver_shapes = [_get_mesh_shape(mesh) for mesh in driver_list]

        for mesh in driven_list:
            _get_mesh_shape(mesh)

        kwargs: dict[str, Any] = {
            "type": "proximityWrap",
        }

        if name:
            kwargs["name"] = name

        created_nodes = cmds.deformer(driven_list, **kwargs) or []

        if not created_nodes:
            raise RuntimeError(f"Could not create proximityWrap on {driven_list}.")

        node = created_nodes[0]

        invalid_drivers = [
            shape
            for shape in driver_shapes
            if not cmds.proximityWrap(
                node,
                query=True,
                canBeAdded=[shape],
            )
        ]

        if invalid_drivers:
            cmds.delete(node)

            raise RuntimeError(
                f"The following meshes could not be added as drivers: {invalid_drivers}"
            )

        # Maya's proximityWrap command accepts one or more shapes through
        # addDrivers.
        cmds.proximityWrap(
            node,
            edit=True,
            addDrivers=driver_shapes,
            applyUserDefaults=True,
        )

        wrap = cls.from_node(node)

        settings = {
            "falloff_scale": falloff_scale,
            "dropoff_rate_scale": dropoff_rate_scale,
            "smooth_influences": smooth_influences,
            "smooth_normals": smooth_normals,
            "span_samples": span_samples,
            "wrap_mode": wrap_mode,
            "max_drivers": max_drivers,
        }

        wrap.set_settings(
            **{setting: value for setting, value in settings.items() if value is not None}
        )

        return wrap

    def add_driven(
        self,
        driven: str | list[str],
    ) -> ProximityWrap:
        """Add one or more meshes to this proximityWrap."""

        if isinstance(driven, str):
            driven = [driven]

        cmds.deformer(
            self.node,
            edit=True,
            geometry=driven,
        )

        self.refresh()
        return self

    @classmethod
    def from_node(cls, node: str) -> ProximityWrap:
        """Read an existing Maya proximityWrap node."""
        _validate_proximity_wrap(node)

        wrap = cls(node=node)
        wrap.refresh()

        return wrap

    def refresh(self) -> ProximityWrap:
        """Refresh all stored information from the Maya node."""
        _validate_proximity_wrap(self.node)

        self.drivers = _get_proximity_wrap_drivers(self.node)
        self.driven = _get_proximity_wrap_driven(self.node)

        self.falloff_scale = self.get_attribute(
            "falloffScale",
            default=1.0,
        )
        self.dropoff_rate_scale = self.get_attribute(
            "dropoffRateScale",
            default=1.0,
        )
        self.smooth_influences = self.get_attribute(
            "smoothInfluences",
            default=0,
        )
        self.smooth_normals = self.get_attribute(
            "smoothNormals",
            default=0,
        )
        self.span_samples = self.get_attribute(
            "spanSamples",
            default=1,
        )
        self.wrap_mode = self.get_attribute(
            "wrapMode",
            default=0,
        )
        self.max_drivers = self.get_attribute(
            "maxDrivers",
            default=0,
        )

        return self

    def get_attribute(
        self,
        attribute: str,
        default: float | bool | str | None = None,
    ) -> int | float | bool | str | None:
        """Get an attribute value from the proximityWrap node."""
        plug = f"{self.node}.{attribute}"

        if not cmds.objExists(plug):
            return default

        return cmds.getAttr(plug)

    def set_attribute(
        self,
        attribute: str,
        value: float | bool | str,
    ) -> ProximityWrap:
        """Set an attribute and refresh the dataclass."""
        plug = f"{self.node}.{attribute}"

        if not cmds.objExists(plug):
            raise ValueError(f"Attribute does not exist: {plug}")

        cmds.setAttr(plug, value)
        return self.refresh()

    def set_settings(
        self,
        *,
        falloff_scale: float | None = None,
        dropoff_rate_scale: float | None = None,
        smooth_influences: int | None = None,
        smooth_normals: int | None = None,
        span_samples: int | None = None,
        wrap_mode: int | None = None,
        max_drivers: int | None = None,
    ) -> ProximityWrap:
        """Set several proximity-wrap settings at once."""
        settings = {
            "falloffScale": falloff_scale,
            "dropoffRateScale": dropoff_rate_scale,
            "smoothInfluences": smooth_influences,
            "smoothNormals": smooth_normals,
            "spanSamples": span_samples,
            "wrapMode": wrap_mode,
            "maxDrivers": max_drivers,
        }

        for attribute, value in settings.items():
            if value is None:
                continue

            plug = f"{self.node}.{attribute}"

            if not cmds.objExists(plug):
                cmds.warning(f"Skipping unavailable proximityWrap setting: {plug}")
                continue

            cmds.setAttr(plug, value)

        self.refresh()
        return self

    def set_falloff(self, value: float) -> ProximityWrap:
        """Set the global falloff scale."""
        if value < 0.0:
            raise ValueError("Falloff scale cannot be negative.")

        return self.set_attribute("falloffScale", value)

    def set_dropoff_rate(self, value: float) -> ProximityWrap:
        """Set the global inverse-distance dropoff-rate scale."""
        if value < 0.0:
            raise ValueError("Dropoff-rate scale cannot be negative.")

        return self.set_attribute("dropoffRateScale", value)

    def set_smoothness(
        self,
        influences: int | None = None,
        normals: int | None = None,
    ) -> ProximityWrap:
        """Set influence and normal smoothing."""
        if influences is not None and influences < 0:
            raise ValueError("Influence smoothing cannot be negative.")

        if normals is not None and normals < 0:
            raise ValueError("Normal smoothing cannot be negative.")

        return self.set_settings(
            smooth_influences=influences,
            smooth_normals=normals,
        )

    def set_wrap_mode(self, value: int) -> ProximityWrap:
        """Set Maya's proximity-wrap mode enum."""
        return self.set_attribute("wrapMode", value)

    def set_span_samples(self, value: int) -> ProximityWrap:
        """Set the number of span samples."""
        if value < 1:
            raise ValueError("Span samples must be at least 1.")

        return self.set_attribute("spanSamples", value)

    def set_max_drivers(self, value: int) -> ProximityWrap:
        """Set the maximum number of contributing drivers."""
        if value < 0:
            raise ValueError("Maximum drivers cannot be negative.")

        return self.set_attribute("maxDrivers", value)

    def add_driver(
        self,
        driver: str,
        apply_user_defaults: bool = True,
    ) -> ProximityWrap:
        """Add another driver mesh."""
        driver_shape = _get_mesh_shape(driver)

        can_be_added = cmds.proximityWrap(
            self.node,
            query=True,
            canBeAdded=[driver_shape],
        )

        if not can_be_added:
            raise RuntimeError(f"{driver} cannot be added as a driver to {self.node}.")

        cmds.proximityWrap(
            self.node,
            edit=True,
            addDrivers=[driver_shape],
            applyUserDefaults=apply_user_defaults,
        )

        self.refresh()
        return self

    def remove_driver(self, driver: str) -> ProximityWrap:
        """Remove a driver mesh."""
        driver_shape = _get_mesh_shape(driver)

        cmds.proximityWrap(
            self.node,
            edit=True,
            removeDrivers=[driver_shape],
        )

        self.refresh()
        return self

    def delete(self) -> None:
        """Delete the proximityWrap node."""
        if cmds.objExists(self.node):
            cmds.delete(self.node)


def create_proximity_wrap(
    driver: str,
    driven: str | list[str],
    name: str | None = None,
    settings: dict[str, int | float] | None = None,
) -> ProximityWrap:
    """Convenience wrapper around ProximityWrap.create()."""
    proximity_wrap = ProximityWrap.create(
        drivers=driver,
        driven=driven,
        name=name,
    )

    if settings:
        for attribute, value in settings.items():
            proximity_wrap.set_attribute(attribute, value)

    return proximity_wrap


def read_proximity_wrap(node: str) -> ProximityWrap:
    """Read an existing proximityWrap into a dataclass."""
    return ProximityWrap.from_node(node)


def _as_list(value: str | list[str]) -> list[str]:
    if isinstance(value, str):
        return [value]

    return list(value)


def _validate_proximity_wrap(node: str) -> None:
    if not cmds.objExists(node):
        raise ValueError(f"Node does not exist: {node}")

    if cmds.nodeType(node) != "proximityWrap":
        raise TypeError(f"{node} is not a proximityWrap node.")


def _get_mesh_shape(mesh: str) -> str:
    """Return the visible mesh shape for a transform or shape."""
    if not cmds.objExists(mesh):
        raise ValueError(f"Mesh does not exist: {mesh}")

    if cmds.nodeType(mesh) == "mesh":
        return mesh

    shapes = (
        cmds.listRelatives(
            mesh,
            shapes=True,
            noIntermediate=True,
            fullPath=True,
            type="mesh",
        )
        or []
    )

    if not shapes:
        raise ValueError(f"{mesh} does not contain a mesh shape.")

    return shapes[0]


def _get_transform(node: str) -> str:
    """Return a transform from a shape or transform."""
    if cmds.nodeType(node) == "transform":
        return node

    parent = (
        cmds.listRelatives(
            node,
            parent=True,
            fullPath=True,
        )
        or []
    )

    return parent[0] if parent else node


def _get_proximity_wrap_drivers(node: str) -> list[str]:
    """Return transforms connected as proximity-wrap drivers."""
    driver_indices = (
        cmds.proximityWrap(
            node,
            query=True,
            driverIndices=True,
        )
        or []
    )

    drivers: list[str] = []

    for index in driver_indices:
        connections = (
            cmds.listConnections(
                f"{node}.drivers[{index}].driverGeometry",
                source=True,
                destination=False,
                shapes=True,
            )
            or []
        )

        for connection in connections:
            transform = _get_transform(connection)

            if transform not in drivers:
                drivers.append(transform)

    return drivers


def _get_proximity_wrap_driven(node: str) -> list[str]:
    """Return transforms deformed by the proximity wrap."""
    geometry = (
        cmds.deformer(
            node,
            query=True,
            geometry=True,
        )
        or []
    )

    return [_get_transform(mesh) for mesh in geometry]
