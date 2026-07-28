from __future__ import annotations

import maya.cmds as cmds

from yrig.control import create_control
from yrig.joint import create_joint
from yrig.spline.matrix_spline.build import matrix_spline_from_transforms
from yrig.transform import create_transform


def get_teeth_locator_indices(cvs_count: int) -> list[int]:
    """Return CV indices that should be used as tooth locator anchors.

    The goal is to sample the spline curve at the start, middle, and quarter points
    so the teeth component gets a simple, evenly spaced placement set.
    """

    if cvs_count <= 1:
        return [0]

    if cvs_count == 2:
        return [0, 1]

    indices = [0]
    for offset in (0.25, 0.5, 0.75):
        index = int(round((cvs_count - 1) * offset))
        if index not in indices:
            indices.append(index)

    if indices[-1] != cvs_count - 1:
        indices.append(cvs_count - 1)

    return sorted(indices)



class TeethSpline:
    def __init__(
        self,
        guides: dict,
        main_ctrl: str,
        joint_parent: str,
        control_grp: str,
        component_grp: str,
        control_size: float = 1.0,
    ):
        self.guides = guides
        self.main_ctrl = main_ctrl
        self.joint_parent = joint_parent
        self.control_grp = control_grp
        self.component_grp = component_grp
        self.control_size = control_size

    def build_single_teeth_spline(self, guide_name: str) -> tuple[object, list[str]]:

        # ------------------------------------------------------------------
        # Sample the guide curve
        # ------------------------------------------------------------------

        cvs = cmds.ls(f"{guide_name}.cv[*]", flatten=True)
        if not cvs:
            return (), []

        indices = get_teeth_locator_indices(len(cvs))

        cv_controls = []

        parent = self.control_grp

        for i, cv_index in enumerate(indices):

            pos = cmds.pointPosition(cvs[cv_index], world=True)
            pos_tuple: tuple[float, float, float] = (
                float(pos[0]),
                float(pos[1]),
                float(pos[2]),
            )

            offset = create_transform(
                name=f"{guide_name}_{i}_ofs",
                parent=parent,
            )

            cmds.xform(offset, worldSpace=True, translation=pos_tuple)

            ctrl = create_control(
                name=f"{guide_name}_{i}",
                parent=offset,
                transform=offset,
                size=self.control_size * 0.5,
                control_shape="circle",
                direction="x",
            )

            cv_controls.append(ctrl.transform)

            parent = ctrl.transform

        # ------------------------------------------------------------------
        # Build the matrix spline
        # ------------------------------------------------------------------

        spline = matrix_spline_from_transforms(
            name=f"{guide_name}_matrixSpline",
            cv_transforms=cv_controls,
            pinned_transforms=5,
            primary_axis=(1, 0, 0),
            secondary_axis=(0, 0, 1),
            padded=False,
            parent=self.component_grp,
        )

        # ------------------------------------------------------------------
        # Create joints on every pinned transform
        # ------------------------------------------------------------------

        joint_parent = self.joint_parent

        joints = []

        for i, pinned in enumerate(spline.pinned_transforms):

            jnt = create_joint(
                name=f"{guide_name}_{i}",
                parent=joint_parent,
                transform=pinned,
            )

            joints.append(jnt)

            joint_parent = jnt

        return spline, joints

    def build_teeth(self) -> None:

        for guide in ("top_teeth", "bottom_teeth"):

            if guide not in self.guides:
                continue

            if not cmds.objExists(self.guides[guide]):
                continue

            self.build_single_teeth_spline(self.guides[guide])
        return