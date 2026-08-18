rom __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from maya import cmds
from maya.api.OpenMaya import MMatrix

_set_attr = cast(Any, cmds.setAttr)


@dataclass
class TransformInfo:
    position: tuple[float, float, float]
    rotation: tuple[float, float, float]
    scale: tuple[float, float, float]
    matrix: MMatrix


@dataclass
class Lattice:
    deformer: str
    lattice: str
    base: str
    driven: list[str]

    lattice_transform: TransformInfo
    base_transform: TransformInfo

    divisions: tuple[int, int, int]
    local_influences: tuple[int, int, int]

    local: bool
    outside_lattice: int
    outside_falloff: float
    freeze_geometry: bool
    bind_original_geometry: bool

    use_partial_resolution: bool
    partial_resolution: float

    # ---------------------------------------------------------
    # GENERIC ATTRIBUTE UTILITIES
    # ---------------------------------------------------------

    def attr(self, attribute: str) -> str:
        """Return a full attribute path on the FFD deformer."""
        return f"{self.deformer}.{attribute}"

    def set(self, attribute: str, value: float | bool) -> None:
        """Set an attribute on the FFD deformer."""
        plug = self.attr(attribute)

        if not cmds.objExists(plug):
            raise AttributeError(f"{self.deformer} has no attribute '{attribute}'")

        _set_attr(plug, value)

    def connect(
        self,
        attribute: str,
        source: str,
        force: bool = True,
    ) -> None:
        """Connect another attribute into an FFD attribute."""
        destination = self.attr(attribute)

        if not cmds.objExists(destination):
            raise AttributeError(f"{self.deformer} has no attribute '{attribute}'")

        cmds.connectAttr(
            source,
            destination,
            force=force,
        )

    def add_driven(self, driven: str) -> None:
        if not cmds.objExists(driven):
            raise ValueError(f"Object does not exist: {driven}")

        if driven in self.driven:
            return

        cmds.lattice(
            self.deformer,
            edit=True,
            geometry=driven,
        )

        self.driven.append(driven)

    def remove_driven(self, driven: str) -> None:
        if driven not in self.driven:
            return

        cmds.lattice(
            self.deformer,
            edit=True,
            geometry=driven,
            remove=True,
        )

        self.driven.remove(driven)

    def get_driven(self) -> list[str]:
        return (
            cmds.lattice(  # type:ignore
                self.deformer,
                query=True,
                geometry=True,
            )
            or []
        )

    def set_divisions(
        self,
        s: int,
        t: int,
        u: int,
    ) -> None:
        lattice_shape = cmds.listRelatives(
            self.lattice,
            shapes=True,
            noIntermediate=True,
        )[0]

        _set_attr(f"{lattice_shape}.sDivisions", s)
        _set_attr(f"{lattice_shape}.tDivisions", t)
        _set_attr(f"{lattice_shape}.uDivisions", u)

        self.divisions = (s, t, u)

    def disconnect(self, attribute: str) -> None:
        """Disconnect an incoming connection from an FFD attribute."""
        destination = self.attr(attribute)

        source = (
            cmds.listConnections(
                destination,
                source=True,
                destination=False,
                plugs=True,
            )
            or []
        )

        for plug in source:
            cmds.disconnectAttr(plug, destination)

    # ---------------------------------------------------------
    # LOCAL MODE
    # ---------------------------------------------------------

    @property
    def driven(self) -> list[str]:
        return (
            cmds.lattice(  # type:ignore
                self.deformer,
                query=True,
                geometry=True,
            )
            or []
        )

    @property
    def local_mode(self) -> bool:
        return bool(cmds.getAttr(self.attr("local")))

    @local_mode.setter
    def local_mode(self, value: bool) -> None:
        _set_attr(self.attr("local"), value)
        self.local = value

    def set_local_influences(
        self,
        s: int,
        t: int,
        u: int,
    ) -> None:
        _set_attr(self.attr("localInfluenceS"), s)
        _set_attr(self.attr("localInfluenceT"), t)
        _set_attr(self.attr("localInfluenceU"), u)

        self.local_influences = (s, t, u)

    # ---------------------------------------------------------
    # OUTSIDE LATTICE
    # ---------------------------------------------------------

    @property
    def outside_mode(self) -> int:
        return cmds.getAttr(self.attr("outsideLattice"))

    @outside_mode.setter
    def outside_mode(self, value: int) -> None:
        """
        0 = inside lattice only
        1 = all points
        2 = falloff
        """
        _set_attr(self.attr("outsideLattice"), value)
        self.outside_lattice = value

    @property
    def outside_falloff_distance(self) -> float:
        return cmds.getAttr(self.attr("outsideFalloffDist"))

    @outside_falloff_distance.setter
    def outside_falloff_distance(self, value: float) -> None:
        _set_attr(
            self.attr("outsideFalloffDist"),
            value,
        )

        self.outside_falloff = value

    # ---------------------------------------------------------
    # RESOLUTION
    # ---------------------------------------------------------

    @property
    def partial_resolution_enabled(self) -> bool:
        return bool(cmds.getAttr(self.attr("usePartialResolution")))

    @partial_resolution_enabled.setter
    def partial_resolution_enabled(
        self,
        value: bool,
    ) -> None:
        _set_attr(
            self.attr("usePartialResolution"),
            value,
        )

        self.use_partial_resolution = value

    @property
    def resolution(self) -> float:
        return cmds.getAttr(self.attr("partialResolution"))

    @resolution.setter
    def resolution(self, value: float) -> None:
        _set_attr(
            self.attr("partialResolution"),
            value,
        )

        self.partial_resolution = value


def get_transform_info(transform: str) -> TransformInfo:
    position = tuple(
        cmds.xform(
            transform,
            query=True,
            worldSpace=True,
            translation=True,
        )  # type:ignore
    )

    rotation = tuple(
        cmds.xform(
            transform,
            query=True,
            worldSpace=True,
            rotation=True,
        )  # type:ignore
    )

    scale = tuple(
        cmds.xform(
            transform,
            query=True,
            relative=True,
            scale=True,
        )  # type:ignore
    )

    matrix_values = cmds.xform(
        transform,
        query=True,
        worldSpace=True,
        matrix=True,
    )

    matrix = MMatrix(matrix_values)

    return TransformInfo(
        position=position,
        rotation=rotation,
        scale=scale,
        matrix=matrix,
    )


def create_lattice(
    driven: str | list[str],
    name: str = "lattice",
    divisions: tuple[int, int, int] = (2, 2, 2),
    local: bool = True,
    local_influences: tuple[int, int, int] = (2, 2, 2),
    outside_lattice: int = 0,
    outside_falloff: float = 1.0,
    freeze_geometry: bool = False,
    bind_original_geometry: bool = False,
    use_partial_resolution: bool = False,
    partial_resolution: float = 0.01,
) -> Lattice:

    if isinstance(driven, str):
        driven = [driven]

    driven = list(driven)

    for node in driven:
        if not cmds.objExists(node):
            raise ValueError(f"Driven object does not exist: {node}")

    result = cmds.lattice(
        driven,  # type:ignore
        divisions=divisions,
        objectCentered=True,
        name=name,
    )

    # cmds.lattice returns:
    #
    # [
    #     lattice transform,
    #     base lattice transform,
    #     ffd deformer
    # ]

    lattice_transform = result[1]  # type:ignore
    base_transform = result[2]  # type:ignore
    deformer = result[0]  # type:ignore

    # ---------------------------------------------------------
    # DEFORMER SETTINGS
    # ---------------------------------------------------------

    _set_attr(
        f"{deformer}.local",
        local,
    )

    _set_attr(
        f"{deformer}.localInfluenceS",
        local_influences[0],
    )

    _set_attr(
        f"{deformer}.localInfluenceT",
        local_influences[1],
    )

    _set_attr(
        f"{deformer}.localInfluenceU",
        local_influences[2],
    )

    _set_attr(
        f"{deformer}.outsideLattice",
        outside_lattice,
    )

    _set_attr(
        f"{deformer}.outsideFalloffDist",
        outside_falloff,
    )

    _set_attr(
        f"{deformer}.freezeGeometry",
        freeze_geometry,
    )

    _set_attr(
        f"{deformer}.bindToOriginalGeometry",
        bind_original_geometry,
    )

    _set_attr(
        f"{deformer}.usePartialResolution",
        use_partial_resolution,
    )

    _set_attr(
        f"{deformer}.partialResolution",
        partial_resolution,
    )

    # ---------------------------------------------------------
    # RETURN WRAPPER
    # ---------------------------------------------------------

    return Lattice(
        deformer=deformer,  # type:ignore
        lattice=lattice_transform,  # type:ignore
        base=base_transform,  # type:ignore
        lattice_transform=get_transform_info(lattice_transform),  # type:ignore
        base_transform=get_transform_info(base_transform),  # type:ignore
        divisions=divisions,
        local_influences=local_influences,
        local=local,
        outside_lattice=outside_lattice,
        outside_falloff=outside_falloff,
        freeze_geometry=freeze_geometry,
        bind_original_geometry=bind_original_geometry,
        use_partial_resolution=use_partial_resolution,
        partial_resolution=partial_resolution,
    )
