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
        setup_parent: str = "rig",
        setup_group: str = "eyes_setup",
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
        self.setup_parent = setup_parent
        self.setup_group = setup_group

        self.blink_guides = {}
        self.blink_curves = {}
        self.blink_blendshapes = {}

    # -------------------
    # Helper Functions
    # -------------------

    def get_curve_mid_y(self, curve: str) -> float:
        """Get the world-space Y of a curve's arc-length midpoint."""
        matrix = self.get_curve_point_matrix(
            curve=curve,
            parameter=0.5,
            tangent_orient=False,
        )
        return matrix[13]

    def create_blink_remap(
        self,
        name: str,
        input_attr: str,
        positions: list[tuple[float, float]],
    ) -> str:
        """
        Build a piecewise-linear remapValue node.

        positions: [(input_position, output_weight), ...]
        """
        positions = sorted(positions, key=lambda item: item[0])

        node = cmds.createNode("remapValue", name=name)

        cmds.connectAttr(input_attr, f"{node}.inputValue")

        cmds.setAttr(f"{node}.inputMin", positions[0][0])  # type:ignore
        cmds.setAttr(f"{node}.inputMax", positions[-1][0])  # type:ignore
        cmds.setAttr(f"{node}.outputMin", 0)  # type:ignore
        cmds.setAttr(f"{node}.outputMax", 1)  # type:ignore

        minimum = positions[0][0]
        span = positions[-1][0] - minimum

        if span <= 1e-8:
            raise ValueError(f"Invalid remap range: {name}")

        for i, (position, weight) in enumerate(positions):
            normalized = (position - minimum) / span

            cmds.setAttr(
                f"{node}.value[{i}].value_Position",
                normalized,  # type:ignore
            )
            cmds.setAttr(
                f"{node}.value[{i}].value_FloatValue",
                weight,  # type:ignore
            )
            # Linear interpolation
            cmds.setAttr(
                f"{node}.value[{i}].value_Interp",
                1,  # type:ignore
            )

        return f"{node}.outValue"

    def build_blink_blendshapes(
        self,
        extension: float = 2.0,
    ) -> None:
        """
        Build upper and lower eyelid blendshape systems.

        Upper eyelid:
            upblink -> upper_rest -> blink -> downblink

        Lower eyelid:
            upblink -> blink -> lower_rest -> downblink

        translateY = 0:
            All blendshape weights are zero.

        Moving toward the outer target:
            Weight increases from 0 to 1 at the guide position.
            Continues extrapolating up to `extension`.

        Moving toward the opposite side:
            The blink target activates first.
            Then fades out as the final target activates.

        Requires:
            self.setup_blink_curves() to have been called.
            self.blink_controls["upper"/"lower"] to exist.
        """

        if extension < 1.0:
            raise ValueError("extension must be >= 1.0")

        # ---------------------------------------------------------
        # Guide midpoint heights
        # ---------------------------------------------------------

        guide_keys = [
            "eyelid_upblink",
            "eyelid_upper_rest",
            "eyelid_blink",
            "eyelid_lower_rest",
            "eyelid_downblink",
        ]

        heights = {key: self.get_curve_mid_y(self.blink_guides[key]) for key in guide_keys}

        up_y = heights["eyelid_upblink"]
        upper_y = heights["eyelid_upper_rest"]
        blink_y = heights["eyelid_blink"]
        lower_y = heights["eyelid_lower_rest"]
        down_y = heights["eyelid_downblink"]

        if not (up_y > upper_y > blink_y > lower_y > down_y):
            raise ValueError(
                "Eyelid guide midpoint Y positions must follow:\n"
                "upblink > upper_rest > blink > lower_rest > downblink\n"
                f"Received: {heights}"
            )

        # ---------------------------------------------------------
        # Initialize storage
        # ---------------------------------------------------------

        self.blink_blendshapes = {}

        configurations = {
            "upper": {
                "rest": "eyelid_upper_rest",
                "targets": [
                    "eyelid_upblink",
                    "eyelid_blink",
                    "eyelid_downblink",
                ],
            },
            "lower": {
                "rest": "eyelid_lower_rest",
                "targets": [
                    "eyelid_upblink",
                    "eyelid_blink",
                    "eyelid_downblink",
                ],
            },
        }

        # ---------------------------------------------------------
        # Build each eyelid
        # ---------------------------------------------------------

        for vertical, config in configurations.items():
            rest_key = config["rest"]
            rest_y = heights[rest_key]  # type:ignore

            # Use duplicated neutral curve from setup_blink_curves().
            curve = self.blink_curves[vertical]

            # Use duplicated targets, not original guides.
            targets = [self.blink_guides[key] for key in config["targets"]]

            # -----------------------------------------------------
            # Create blendShape
            # -----------------------------------------------------

            blendshape = cmds.blendShape(
                *targets,
                curve,
                name=f"{vertical}_blink_{self.side}_BS",
                frontOfChain=True,
            )[0]  # type:ignore

            # Allow weights greater than 1 for extrapolation.
            cmds.setAttr(
                f"{blendshape}.weight",
                size=len(targets),
            )

            # -----------------------------------------------------
            # Calculate relative Y distances
            # -----------------------------------------------------

            up_pos = up_y - rest_y
            blink_pos = blink_y - rest_y
            down_pos = down_y - rest_y

            control = self.blink_controls[vertical].transform
            input_attr = f"{control}.translateY"

            # -----------------------------------------------------
            # Piecewise weight mappings
            #
            # Each point is:
            #     (translateY, blendshape_weight)
            #
            # The remap helper normalizes the input positions
            # and interpolates linearly between them.
            # -----------------------------------------------------

            if vertical == "upper":
                # Rest -> upblink -> extended upblink
                up_points = [
                    (down_pos, 0.0),
                    (0.0, 0.0),
                    (up_pos, 1.0),
                    (up_pos * extension, extension),
                ]

                # Rest -> blink -> downblink
                blink_points = [
                    (down_pos, 0.0),
                    (blink_pos, 1.0),
                    (0.0, 0.0),
                    (up_pos * extension, 0.0),
                ]

                # Blink -> downblink
                down_points = [
                    (down_pos * extension, extension),
                    (blink_pos, 0.0),
                    (0.0, 0.0),
                    (up_pos * extension, 0.0),
                ]

            else:
                # Blink -> upblink
                up_points = [
                    (down_pos * extension, 0.0),
                    (0.0, 0.0),
                    (blink_pos, 0.0),
                    (up_pos * extension, extension),
                ]

                # Rest -> blink -> upblink
                blink_points = [
                    (down_pos * extension, 0.0),
                    (0.0, 0.0),
                    (blink_pos, 1.0),
                    (up_pos, 0.0),
                ]

                # Rest -> downblink -> extended downblink
                down_points = [
                    (down_pos * extension, extension),
                    (down_pos, 1.0),
                    (0.0, 0.0),
                    (up_pos, 0.0),
                ]

            mappings = [
                ("upblink", up_points),
                ("blink", blink_points),
                ("downblink", down_points),
            ]

            # -----------------------------------------------------
            # Create remap nodes and connect blendshape weights
            # -----------------------------------------------------

            for index, (target_name, points) in enumerate(mappings):
                # remapValue output is normalized to 0..1.
                # Scale back to the desired maximum weight.
                maximum_weight = max(weight for _, weight in points)

                normalized_points = [
                    (position, weight / maximum_weight) for position, weight in points
                ]

                output = self.create_blink_remap(
                    name=f"{vertical}_{target_name}_{self.side}_RMV",
                    input_attr=input_attr,
                    positions=normalized_points,
                )

                multiplier = cmds.createNode(
                    "multiplyDivide",
                    name=f"{vertical}_{target_name}_{self.side}_MD",
                )

                cmds.setAttr(
                    f"{multiplier}.input2X",
                    maximum_weight,  # type:ignore
                )

                cmds.connectAttr(
                    output,
                    f"{multiplier}.input1X",
                )

                cmds.connectAttr(
                    f"{multiplier}.outputX",
                    f"{blendshape}.weight[{index}]",
                    force=True,
                )

            # -----------------------------------------------------
            # Store results
            # -----------------------------------------------------

            self.blink_blendshapes[vertical] = blendshape

    def setup_blink_curves(self) -> None:
        """
        Create the hidden eyelid blendshape setup.

        Hierarchy:
            rig
                eyes_setup
                    eye_blink_L_grp
                        duplicated guides
                        upper_blink_curve_L
                        lower_blink_curve_L

        The original guide curves remain untouched.
        """

        # ----------------------------------------
        # Shared setup group
        # ----------------------------------------

        if not cmds.objExists(self.setup_parent):
            raise ValueError(f"Eye setup parent does not exist: {self.setup_parent}")

        if cmds.objExists(self.setup_group):
            self.eyes_setup_grp = self.setup_group
        else:
            self.eyes_setup_grp = create_transform(
                name=self.setup_group,
                parent=self.setup_parent,
            )

        # ----------------------------------------
        # Side-specific group
        # ----------------------------------------

        side_group_name = f"eye_blink_{self.side}_grp"

        if cmds.objExists(side_group_name):
            raise ValueError(f"Blink setup already exists: {side_group_name}")

        self.blink_setup_grp = create_transform(
            name=side_group_name,
            parent=self.eyes_setup_grp,
        )

        # ----------------------------------------
        # Duplicate all five guide curves
        # ----------------------------------------

        guide_keys = [
            "eyelid_upblink",
            "eyelid_upper_rest",
            "eyelid_blink",
            "eyelid_lower_rest",
            "eyelid_downblink",
        ]

        for key in guide_keys:
            source_curve = self.guides[key]

            if not cmds.objExists(source_curve):
                raise ValueError(f"Missing eyelid guide: {source_curve}")

            duplicate_name = f"{key}_{self.side}_target"

            duplicate = cmds.duplicate(
                source_curve,
                name=duplicate_name,
                returnRootsOnly=True,
            )[0]

            cmds.parent(
                duplicate,
                self.blink_setup_grp,
            )

            self.blink_guides[key] = duplicate

        # ----------------------------------------
        # Duplicate the two neutral/rest curves
        # ----------------------------------------

        for vertical in ("upper", "lower"):
            rest_key = f"eyelid_{vertical}_rest"

            curve = cmds.duplicate(
                self.blink_guides[rest_key],
                name=f"{vertical}_blink_curve_{self.side}",
                returnRootsOnly=True,
            )[0]

            cmds.parent(
                curve,
                self.blink_setup_grp,
            )

            self.blink_curves[vertical] = curve

        # ----------------------------------------
        # Hide shared setup hierarchy
        # ----------------------------------------

        cmds.setAttr(
            f"{self.eyes_setup_grp}.visibility",
            False,  # type:ignore
        )

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

        # Build hidden setup hierarchy and duplicate guides
        self.setup_blink_curves()

        # Connect blink controls to blendshape curves
        self.build_blink_blendshapes(extension=2.0)

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
