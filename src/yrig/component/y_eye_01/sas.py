import maya.cmds as cmds

from yrig.transform.utils import match_location


class Socket:
    def __init__(
        self,
        side: str = "L",
        guides: dict = {},
        control_size: float = 1.0,
        main_ctrl: str = "",
        parent: str = "",
        joint_parent: str = "",
        component_grp: str = "",
        control_grp: str = "",
    ) -> None:
        self.side = side
        self.guides = guides
        self.main_ctrl = main_ctrl
        self.control_size = control_size
        self.parent = parent
        self.joint_parent = joint_parent
        self.component_grp = component_grp
        self.control_grp = control_grp

    # -------------------
    # Helper Functions
    # -------------------

    def get_nurbs_surface_radius(self, obj: str) -> float:
        """
        Returns the radius of a NURBS circle.

        Args:
            obj (str): Transform of the NURBS circle

        Returns:
            float: radius
        """

        bbox: list[int | float] = cmds.exactWorldBoundingBox(obj)

        x: int | float = bbox[3] - bbox[0]
        y: int | float = bbox[4] - bbox[1]
        z: int | float = bbox[5] - bbox[2]

        return max(x, y, z) * 0.5

    def create_proxy_cube(self, size_guide: str, pos_guide: str, offset_size: float = 1.2) -> str:
        # 1. radius from circle
        radius = self.get_nurbs_surface_radius(size_guide)

        # 2. position from guide

        # 3. cube size = diameter * offset
        diameter = radius * 2.0
        cube_size = diameter * offset_size

        # 4. create cube
        cube: tuple[str | str] = cmds.polyCube(  # type:ignore
            width=cube_size,
            height=cube_size,
            depth=cube_size,
            name=f"eye_lattice_proxy_{self.side}",
        )

        # 5. place cube at position

        match_location(transform=cube[0], target_transform=pos_guide)

        return cube[0]

    def create_lattice(self, input_object: str, division: tuple, resolution: tuple) -> None:

        pass

    def build_sas(self) -> None:
        pass
