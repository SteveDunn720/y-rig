from __future__ import annotations

from typing import cast

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

        # Create Joint Chain

        guide_order = [
            "tongue_back",
            "tongue2",
            "tongue3",
            "tongue4",
            "tongue5",
            "tongue_front",
        ]

        jaw_guide = ["jaw_M_jnt"]

        self.joints = []

        joint_parent = self.joint_parent if cmds.objExists(self.joint_parent) else None
        control_parent = self.control_grp

        temp_ctrls = []
        ctrl_tran = None

        for i, guide in enumerate(guide_order):
            if i == 0:
                ctrl_tran = create_transform(
                    name=f"{guide}_ofst",
                    transform=jaw_guide[0],
                    parent=control_parent,
                )

                ctrl = create_control(
                    name=f"{guide}_ctrl",
                    parent=ctrl_tran,
                    transform=self.guides[guide],
                    size=self.control_size * 0.5,
                    control_shape="circle",
                    direction="x",
                )
            else:
                ctrl = create_control(
                    name=f"{guide}_ctrl",
                    parent=control_parent,
                    transform=self.guides[guide],
                    size=self.control_size * 0.5,
                    control_shape="circle",
                    direction="x",
                )

            temp_ctrls.append(ctrl)

            joint = create_joint(
                name=guide,
                parent=joint_parent,
                transform=ctrl,
                connect=False,
            )

            self.joints.append(joint)

            joint_parent = joint

            control_parent = ctrl.transform

        # Orient Joint Chain

        cmds.joint(
            self.joints[0],
            edit=True,
            orientJoint="xyz",
            secondaryAxisOrient="yup",
            children=True,
            zeroScaleOrient=True,
        )

        # Create Spline IK

        ik_result = cast(
            tuple[str, str, str],
            cmds.ikHandle(
                startJoint=self.joints[0],
                endEffector=self.joints[-1],
                solver="ikSplineSolver",
                createCurve=True,
                parentCurve=False,
            ),
        )
        ik_handle, effector, curve = ik_result

        ik_handle = cmds.rename(
            ik_handle,
            "tongue_ikh",
        )

        curve = cmds.rename(
            curve,
            "tongue_crv",
        )

        # Rebuild Curve

        cmds.rebuildCurve(
            curve,
            constructionHistory=False,
            replaceOriginal=True,
            rebuildType=0,
            endKnots=1,
            keepRange=0,
            keepControlPoints=False,
            keepEndPoints=True,
            keepTangents=False,
            spans=4,
            degree=3,
        )

        # Create Clusters

        cvs = cmds.ls(
            f"{curve}.cv[*]",
            flatten=True,
        )

        cluster_sets = [
            cvs[0:2],
            [cvs[2]],
            [cvs[3]],
            [cvs[4]],
            cvs[5:7],
        ]

        controls = []

        first_ctrl = temp_ctrls[0]
        first_ctrl_transform = (
            first_ctrl.transform if hasattr(first_ctrl, "transform") else first_ctrl
        )

        parent = cmds.listRelatives(
            first_ctrl_transform,
            parent=True,
            fullPath=False,
        )[0]

        for i, cv_set in enumerate(cluster_sets):
            cluster, handle = cast(
                tuple[str, str],
                cmds.cluster(
                    *cv_set,
                    name=f"tongue_cluster_{i}",
                ),
            )

            cmds.parent(handle, self.component_grp)

            offset = create_transform(
                name=f"tongue_{i}_ofs",
                parent=parent,
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
                ctrl_transform,
                handle,
                maintainOffset=True,
            )

            controls.append(ctrl)

            # Make the next offset a child of this control
            parent = ctrl_transform

        # Cleanup

        # Delete Temporary Joint Controls
        for ctrl in temp_ctrls:
            ctrl_transform = ctrl.transform if hasattr(ctrl, "transform") else ctrl

            if cmds.objExists(ctrl_transform):
                cmds.delete(ctrl_transform)

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

        if cmds.objExists("jaw_M_ctl"):
            cmds.connectAttr(
                f"{jaw_guide[0]}.rotate",
                f"{ctrl_tran}.rotate",
                force=True,
            )

        # ---------------------------------------------------------------------
        # Stretchy Spline IK
        # ---------------------------------------------------------------------

        # Get the curve shape and original shape
        curve_shapes = cmds.listRelatives(curve, shapes=True, fullPath=False) or []

        curve_shape = None
        curve_shape_orig = None

        for shape in curve_shapes:
            if shape.endswith("ShapeOrig"):
                curve_shape_orig = shape
            elif shape.endswith("Shape"):
                curve_shape = shape

        if curve_shape and curve_shape_orig:
            # Current curve length
            current_curve_info = cmds.createNode(
                "curveInfo",
                name="tongue_current_curveInfo",
            )
            cmds.connectAttr(
                f"{curve_shape}.worldSpace[0]",
                f"{current_curve_info}.inputCurve",
                force=True,
            )

            # Original curve length
            original_curve_info = cmds.createNode(
                "curveInfo",
                name="tongue_original_curveInfo",
            )
            cmds.connectAttr(
                f"{curve_shape_orig}.worldSpace[0]",
                f"{original_curve_info}.inputCurve",
                force=True,
            )

            # Stretch ratio = currentLength / originalLength
            stretch_md = cmds.createNode(
                "multiplyDivide",
                name="tongue_stretch_md",
            )
            cmds.setAttr(f"{stretch_md}.operation", 2)  # type: ignore # Divide

            scale_md = cmds.createNode(
                "multiplyDivide",
                name="tongue_scale_md",
            )
            cmds.setAttr(f"{scale_md}.operation", 2)  # type: ignore # Divide

            cmds.connectAttr(
                f"{current_curve_info}.arcLength",
                f"{stretch_md}.input1X",
                force=True,
            )
            cmds.connectAttr(
                f"{original_curve_info}.arcLength",
                f"{stretch_md}.input2X",
                force=True,
            )

            cmds.connectAttr(
                f"{stretch_md}.outputX",
                f"{scale_md}.input1X",
            )

            cmds.connectAttr(
                "world_ctl.scaleX",
                f"{scale_md}.input2X",
            )

            # Drive the first tongue joint scale
            axises = ["X", "Y", "Z"]
            for axis in axises:
                cmds.connectAttr(
                    f"{scale_md}.outputX",
                    f"tongue_back_jnt.scale{axis}",
                    force=True,
                )
