import math

from maya import cmds
from maya.api.OpenMaya import (
    MEulerRotation,
    MFnNurbsCurve,
    MMatrix,
    MPoint,
    MSelectionList,
    MSpace,
    MTransformationMatrix,
    MVector,
)

from yrig.control import ControlShape, create_control
from yrig.joint import create_joint
from yrig.transform import create_transform


class Eyelid:
    def __init__(
        self,
        side: str,
        guides: dict,
        main_ctrl: str,
        parent: str,
        joint_parent: str,
        component_grp: str,
        control_grp: str,
        control_size: float = 1.0,
    ) -> None:
        if guides is None:
            guides = {}
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

    def get_curve_point_matrix(
        self,
        curve: str,
        parameter: float,
        tangent_orient: bool = True,
        up_vector: tuple[float, float, float] = (0, 1, 0),
        aim_axis: str = "x",
        mirror: bool = False,
        mirror_axis: str = "x",
    ) -> MMatrix:
        """
        Get a world-space matrix at a normalized curve parameter.

        When mirror=True:
            1. Reflect the curve position and tangent into mirrored space.
            2. Construct the orientation in mirrored space.
            3. Reflect the completed matrix back across the mirror axis.

        The resulting position matches the original curve, while
        the orientation follows the mirrored construction.

        Args:
            curve: NURBS curve transform or shape.
            parameter: Normalized arc-length parameter (0.0-1.0).
            tangent_orient: Orient along the curve tangent.
            up_vector: World-space reference up vector.
            aim_axis: Local axis aligned with tangent ('x', 'y', 'z').
            mirror: Enable mirrored orientation construction.
            mirror_axis: World reflection axis ('x', 'y', 'z').

        Returns:
            World-space MMatrix.
        """

        # ---------------------------------------------------------
        # Resolve curve shape
        # ---------------------------------------------------------

        if cmds.nodeType(curve) == "nurbsCurve":
            shape = curve
        else:
            shapes = (
                cmds.listRelatives(
                    curve,
                    shapes=True,
                    noIntermediate=True,
                    type="nurbsCurve",
                    fullPath=True,
                )
                or []
            )

            if not shapes:
                raise ValueError(f"No NURBS curve found: {curve}")

            shape = shapes[0]

        selection = MSelectionList()
        selection.add(shape)

        dag_path = selection.getDagPath(0)
        fn_curve = MFnNurbsCurve(dag_path)

        # ---------------------------------------------------------
        # Sample curve
        # ---------------------------------------------------------

        parameter = max(0.0, min(1.0, parameter))

        length = fn_curve.length()
        curve_param = fn_curve.findParamFromLength(length * parameter)

        position = fn_curve.getPointAtParam(
            curve_param,
            MSpace.kWorld,
        )

        tangent = fn_curve.tangent(
            curve_param,
            MSpace.kWorld,
        ).normal()

        # ---------------------------------------------------------
        # Reflection helpers
        # ---------------------------------------------------------

        axis = mirror_axis.lower()

        if axis not in ("x", "y", "z"):
            raise ValueError("mirror_axis must be 'x', 'y', or 'z'")

        axis_index = {"x": 0, "y": 1, "z": 2}[axis]

        def reflect(vector: MVector) -> MVector:
            values = [vector.x, vector.y, vector.z]
            values[axis_index] *= -1
            return MVector(*values)

        # ---------------------------------------------------------
        # Mirror curve sample BEFORE constructing orientation
        # ---------------------------------------------------------

        if mirror:
            position = MPoint(
                *reflect(
                    MVector(
                        position.x,
                        position.y,
                        position.z,
                    )
                )
            )

            tangent = reflect(tangent)

        # ---------------------------------------------------------
        # Construct orientation
        # ---------------------------------------------------------

        if tangent_orient:
            aim = tangent.normal()
            up = MVector(*up_vector).normal()

            # Avoid parallel aim/up vectors.
            if abs(aim * up) > 0.999:
                fallback = MVector(0, 0, 1) if abs(aim.z) < 0.999 else MVector(1, 0, 0)
                up = fallback

            side = (aim ^ up).normal()
            up = (side ^ aim).normal()

            if aim_axis.lower() == "x":
                x_axis = aim
                y_axis = up
                z_axis = side

            elif aim_axis.lower() == "y":
                x_axis = -side
                y_axis = aim
                z_axis = up

            elif aim_axis.lower() == "z":
                x_axis = up
                y_axis = -side
                z_axis = aim

            else:
                raise ValueError("aim_axis must be 'x', 'y', or 'z'")

        else:
            x_axis = MVector(1, 0, 0)
            y_axis = MVector(0, 1, 0)
            z_axis = MVector(0, 0, 1)

        # ---------------------------------------------------------
        # Build matrix in sampled space
        # ---------------------------------------------------------

        matrix = MMatrix(
            [
                x_axis.x,
                x_axis.y,
                x_axis.z,
                0.0,
                y_axis.x,
                y_axis.y,
                y_axis.z,
                0.0,
                z_axis.x,
                z_axis.y,
                z_axis.z,
                0.0,
                position.x,
                position.y,
                position.z,
                1.0,
            ]
        )

        # ---------------------------------------------------------
        # Reflect completed matrix back across world axis
        # ---------------------------------------------------------

        if mirror:
            scale = [1.0, 1.0, 1.0]
            scale[axis_index] = -1.0

            mirror_matrix = MMatrix(
                [
                    scale[0],
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    scale[1],
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    scale[2],
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                ]
            )

            # Maya uses row-vector matrix convention.
            # Reflect the world-space matrix back.
            matrix = matrix * mirror_matrix

        return matrix

    def convert_to_matrix(
        self,
        pos: tuple[float, float, float] = (0, 0, 0),
        rot: tuple[float, float, float] = (0, 0, 0),
        scale: tuple[float, float, float] = (1, 1, 1),
    ) -> MMatrix:
        """
        Build an MMatrix from translation, rotation, and scale.
        """

        m = MTransformationMatrix()

        # Translation
        m.setTranslation(MVector(*pos), MSpace.kWorld)

        # Rotation (Euler degrees → radians internally handled by API)
        euler = MEulerRotation(
            math.radians(rot[0]),
            math.radians(rot[1]),
            math.radians(rot[2]),
        )
        m.setRotation(euler)

        # Scale
        m.setScale(scale, MSpace.kWorld)

        return m.asMatrix()

    def build(
        self,
        sub_divisions: int = 7,
    ) -> None:
        #######
        # Set up look follow
        #######

        self.sub_eyelid_controls = []
        self.sub_joints = []

        self.look_offset = create_transform(
            name=f"look_offset_{self.side}",
            parent=self.main_ctrl,
            transform=self.guides["center_piv"],
        )
        self.sub_grp = create_transform(
            name=f"sub_controls_{self.side}",
            parent=self.main_ctrl,
            transform=self.guides["center_piv"],
        )

        ##########
        # Main Control Behavior
        ##########

        self.blink_controls = {}
        for vertical in ["upper", "lower"]:
            side_mod = -1 if self.side == "R" else 1
            blink_matrix = self.get_curve_point_matrix(
                curve=self.guides[f"eyelid_{vertical}_rest"],
                parameter=0.5,
                tangent_orient=False,
                mirror=self.side == "R",
            )

            self.blink_controls[vertical] = create_control(
                name=f"{vertical}_blink_{self.side}",
                parent=self.main_ctrl,
                transform=blink_matrix,
                size=self.control_size,
                control_shape=ControlShape.SEMI_CIRCLE,
                direction="z",
                dimensions=(1, 1, 1 if vertical == "upper" else -1),
                position_offset=(0, 0, 1),
            )

        for vertical in ["upper", "lower"]:
            for i in range(sub_divisions):
                percent = i / (sub_divisions - 1)
                matrix = self.get_curve_point_matrix(
                    curve=self.guides[f"eyelid_{vertical}_rest"],
                    parameter=percent,
                    tangent_orient=True,
                )

                sub_ctrl = create_control(
                    name=f"{vertical}_{i}_{self.side}",
                    parent=self.sub_grp,
                    transform=matrix,
                    size=self.control_size / 10,
                    control_shape="circle",
                    direction="z",
                )
                sub_jnt = create_joint(
                    name=f"{vertical}_{i}_{self.side}",
                    parent=self.joint_parent,
                    transform=sub_ctrl.transform,
                )

                self.sub_eyelid_controls.append(sub_ctrl)
                self.sub_joints.append(sub_jnt)
