
from typing import Any

import maya.cmds as cmds
from yrig.control import create_control
from yrig.joint import create_joint
from yrig.transform import create_transform
from maya.api.OpenMaya import MMatrix, MTransformationMatrix, MVector, MEulerRotation,MSpace
from yrig.transform.utils import get_position
import math


class Eyelid():
    def __init__(self, side="L", guides={}, control_size=1, main_ctrl=None, parent=None):
        self.side = side
        self.guides = guides
        self.main_ctrl = main_ctrl
        self.control_size=control_size
        self.parent = parent
    
    # -------------------
    # Helper Functions
    # -------------------
    def convert_to_matrix(
        self,
        pos=(0, 0, 0),
        rot=(0, 0, 0),
        scale=(1, 1, 1),
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

        
    def get_flat_y_aim_rotation(self, source:str=None, target:str=None) -> float:
        """
        Returns Y-axis rotation (degrees) from source → target,
        ignoring Y height (XZ plane only).
        """

        p1: Any = get_position(transform=source)
        p2: Any = get_position(transform=target)

        # Flatten Y
        dx = p2.x - p1.x
        dz = p2.z - p1.z

        # Angle in radians
        angle = math.atan2(dx, dz)

        # Convert to degrees
        return math.degrees(angle)

    def soft_colide(self, Upper_driver:str=None, Lower_driver:str=None, parent:str=None, push=.5,):



        ctrl_list = [Lower_driver, Upper_driver]

        out_matrix = []

        # shared logic to check how close our two drivers are 

        pma_calc = cmds.createNode('plusMinusAverage', name=f'{Upper_driver}_{Lower_driver}_PMA')
        cmds.setAttr(f'{pma_calc}.operation', 2)

        condition = cmds.createNode('condition', name=f'{Upper_driver}_{Lower_driver}_COND')
        cmds.setAttr(f'{condition}.operation', 2)
        cmds.setAttr(f'{condition}.colorIfFalseR', 0)
        cmds.connectAttr(f'{pma_calc}.output1D', f'{condition}.colorIfTrueR')
        cmds.connectAttr(f'{pma_calc}.output1D', f'{condition}.firstTerm')

        for ctrl in ctrl_list:
            #matix calc
            mult_matrix = cmds.createNode('multMatrix', name=f'{ctrl}_MM')
            dec_matrix = cmds.createNode('decomposeMatrix',  name=f'{ctrl}_DM')

            cmds.connectAttr(f'{ctrl}.worldMatrix[0]', f'{mult_matrix}.matrixIn[0]')
            cmds.connectAttr(f'{parent}.worldInverseMatrix[0]', f'{mult_matrix}.matrixIn[1]')
            cmds.connectAttr(f'{mult_matrix}.matrixSum', f'{dec_matrix}.inputMatrix')

            if ctrl == ctrl_list[0]:
                cmds.connectAttr(f'{dec_matrix}.outputTranslateY', f'{pma_calc}.input1D[0]')
            else:
                cmds.connectAttr(f'{dec_matrix}.outputTranslateY', f'{pma_calc}.input1D[1]')

            out_matrix.append(dec_matrix)

            # push logic

            push_mult = cmds.createNode('multiplyDivide', name = f'{ctrl}_MD')
            cmds.setAttr(f'{push_mult}.input2X', .5 if ctrl == ctrl_list[0] else -.5)
            cmds.connectAttr(f'{condition}.outColorR', f'{push_mult}.input1X')

            pma_drive = cmds.createNode('plusMinusAverage', name=f'{ctrl}_PMA')
            cmds.setAttr(f'{pma_drive}.operation', 2)
            axis = 'X' if ctrl == ctrl_list[0] else 'Y'
            cmds.connectAttr(f'{dec_matrix}.outputTranslateY', f'{pma_drive}.input1D[0]')
            cmds.connectAttr(f'{push_mult}.outputX', f'{pma_drive}.input1D[1]')




    def build_blink(self, z_offset:int=1, x_offset:int=1):
        ### get middle x pos for the blink

        upper_pos: Any = get_position(transform=self.guides["eyelid_upper"])
        lower_pos: Any = get_position(transform=self.guides["eyelid_upper"])

        blink_x:int = (upper_pos.x + lower_pos.x)/2
        blink_z:int = (upper_pos.z + lower_pos.z)/2 + z_offset

        self.main_blink_controls = []
        self.sub_blink_controls = {}

        sub_transform_grp = create_transform(
                name=f'sub_blink_offset_matrix_drivers',
                parent=self.main_ctrl,
                transform=self.guides[f"center_piv"],
                )

        #pper_matrix: Any = self.convert_to_matrix(pos=(blink_x, upper_pos.y, blink_z))
        #lower_matrix: Any = self.convert_to_matrix(pos=(blink_x, lower_pos.y, blink_z))

        for side in ['upper', 'lower']:
            blink_matrix: Any = self.convert_to_matrix(pos=(blink_x, upper_pos.y, blink_z))
            blink_ctrl = create_control(
                    name=f'{side}_blink_{self.side}',
                    parent=self.main_ctrl,
                    transform=blink_matrix,
                    size=self.control_size,
                    control_shape=f'{side}_semi_circle',
                    direction='z'
                )
            self.main_blink_controls.append[blink_ctrl]  # pyright: ignore[reportIndexIssue]

        for sub_blink in ['inner', 'mid', 'outer']:
            for side in ['upper', 'lower']:

                #setting up mods

                side_mod = 1 if self.side == 'L' else -1

                if sub_blink == "inner":
                    mod = -1
                elif sub_blink == "mid":
                    mod = 0
                else:
                    mod = -1

                new_matrix: Any = self.convert_to_matrix(pos=(blink_x + (mod * side_mod) , upper_pos.y, blink_z))

                #building sub controls

                self.sub_blink_controls[f"{sub_blink}_{side}_blink_ctrl"] = create_control(
                    name=f'{sub_blink}_{side}_blink_{self.side}',
                    parent=self.main_ctrl,
                    transform=new_matrix,
                    size=self.control_size,
                    control_shape='sphere',
                    direction='z'
                )

                #setting up blink driver groups

                aim: float = self.get_flat_y_aim_rotation(source=self.guides["center_piv"], target=self.guides[f"eyelid_{sub_blink}_{side}"])

                driver_offset: str = create_transform(
                name=f'{sub_blink}_{side}_blink_offset',
                parent=self.main_ctrl,
                transform=self.guides["center_piv"]
                )

                driver_driven: str = create_transform(
                name=f'{sub_blink}_{side}_blink_driven',
                parent=driver_offset,
                transform=self.guides["center_piv"]
                )

                driver_driver: str = create_transform(
                name=f'{sub_blink}_{side}_blink_driver',
                parent=driver_driven,
                transform=self.guides["center_piv"]
                )

                cmds.setAttr(f'{driver_offset}.rotateY', aim)

                driven_transform = create_transform(
                name=f'{sub_blink}_{side}_blink_offset',
                parent=self.main_ctrl,
                transform=self.guides[f"eyelid_{sub_blink}_{side}"],
                )
                
                #temp visualization will remove later
                sphere = cmds.polySphere(name="mySphere")[0]
                cmds.delete(cmds.parentConstraint(driven_transform, sphere))
                cmds.parent(sphere, driven_transform)







