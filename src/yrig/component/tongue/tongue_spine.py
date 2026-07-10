from __future__ import annotations

import maya.cmds as cmds

from yrig.control import create_control
from yrig.joint import create_joint
from yrig.transform import create_transform


class TongueSpine:
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

    def build_tongue_spine(self) -> None:

        # --------------------------------------------------------
        # Create Joint Chain
        # --------------------------------------------------------

        guide_order = [
            "tongue_back",
            "tongue2",
            "tongue3",
            "tongue4",
            "tongue5",
            "tongue_front",
        ]

        self.joints = []
        parent = self.joint_parent

        for guide in guide_order:
            joint = create_joint(
                name=f"{guide}_jnt",
                parent=parent,
                transform=self.guides[guide],
            )

            # If create_joint returns an object instead of a string,
            # uncomment the next line.
            # joint = joint.transform

            self.joints.append(joint)
            parent = joint

        cmds.joint(
            self.joints[0],
            edit=True,
            orientJoint="xyz",
            secondaryAxisOrient="yup",
            children=True,
            zeroScaleOrient=True,
        )

        # --------------------------------------------------------
        # Create Spline IK
        # --------------------------------------------------------

        ik_handle, effector, curve = cmds.ikHandle(
            startJoint=self.joints[0],
            endEffector=self.joints[-1],
            solver="ikSplineSolver",
            createCurve=True,
            parentCurve=False,
        )  # type: ignore

        ik_handle = cmds.rename(ik_handle, "tongue_ikh")
        curve = cmds.rename(curve, "tongue_crv")

        # --------------------------------------------------------
        # Rebuild Curve
        # --------------------------------------------------------

        cmds.rebuildCurve(
            curve,
            ch=False,  # type: ignore
            rpo=True,  # type: ignore
            rt=0,  # type: ignore
            end=1,  # type: ignore
            kr=0,  # type: ignore
            kcp=False,  # type: ignore
            kep=True,  # type: ignore
            kt=False,  # type: ignore
            s=4,  # type: ignore
            d=3,  # type: ignore
        )

        # --------------------------------------------------------
        # Create Clusters
        # --------------------------------------------------------

        cvs = cmds.ls(f"{curve}.cv[*]", flatten=True)

        cluster_sets = [
            cvs[:2],  # first two cvs
            [cvs[2]],
            [cvs[3]],
            cvs[-2:],  # last two cvs
        ]

        controls = []

        for i, cv_set in enumerate(cluster_sets):
            cluster, handle = cmds.cluster(
                cv_set,  # type: ignore
                name=f"tongue_cluster_{i}",
            )  # type: ignore

            cmds.parent(handle, self.component_grp)

            offset = create_transform(
                name=f"tongue_{i}_ofs",
                parent=self.control_grp,
            )

            cmds.matchTransform(offset, handle)

            ctrl = create_control(
                name=f"tongue_{i}",
                parent=offset,
                transform=offset,
                size=self.control_size,
                control_shape="circle",
                direction="x",
            )

            ctrl_transform = ctrl.transform if hasattr(ctrl, "transform") else ctrl

            cmds.parentConstraint(
                ctrl_transform,  # type: ignore
                handle,
                maintainOffset=True,
            )

            controls.append(ctrl)

        # --------------------------------------------------------
        # Cleanup
        # --------------------------------------------------------

        cmds.parent(
            ik_handle,
            curve,
            self.component_grp,
        )

        cmds.hide(
            ik_handle,
            curve,
        )

        self.controls = controls
        self.curve = curve
        self.ik_handle = ik_handle
