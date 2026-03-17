from typing import TYPE_CHECKING

import mgear.pymaya as pm
from mgear.core import attribute, primitive, transform
from mgear.pymaya import datatypes
from mgear.shifter import component

from yrig.spline.matrix_spline.build import matrix_spline_from_transforms

if TYPE_CHECKING:
    from mgear.pymaya.datatypes import Matrix

##########################################################
# COMPONENT
##########################################################


class Component(component.Main):
    """Shifter component Class"""

    # =====================================================
    # OBJECTS
    # =====================================================
    def addObjects(self):
        """Add all the objects needed to create the component."""
        self.WIP = self.options["mode"]

        # CV controllers ------------------------------------
        t = self.guide.tra["root"]
        self.cv_guide_transforms: list[Matrix] = self.guide.atra

        self.component_space = primitive.addTransform(
            self.root,
            self.getName("space"),
            transform.setMatrixScale(self.guide.tra["root"], [1, 1, 1]),
        )
        parent = self.component_space
        self.cv_npo_transforms = []
        self.cv_ctls = []
        for i, t in enumerate(self.cv_guide_transforms):
            normalized_transform = transform.setMatrixScale(t, [1, 1, 1])
            cv_npo = primitive.addTransform(
                parent, self.getName(f"cv{i}_npo"), normalized_transform
            )
            self.cv_npo_transforms.append(cv_npo)
            cv_ctl = self.addCtl(
                cv_npo,
                f"cv{i}_ctl",
                normalized_transform,
                self.color_ik,
                "sphere",
                w=self.size * 0.15,
                h=self.size * 0.15,
                d=self.size * 0.15,
                ro=datatypes.Vector([0, 0, 1.5708]),
                tp=self.parentCtlTag,
            )
            self.cv_ctls.append(cv_ctl)
            attribute.setKeyableAttributes(cv_ctl)

        # Divisions
        self.div_cns = []
        self.upv_cns = []

        if self.settings["overrideJntNb"]:
            self.def_number = self.settings["jntNb"]
        else:
            self.def_number = len(self.guide.apos)

        self.matrix_spline = matrix_spline_from_transforms(
            name=self.getName("spline"),
            cv_transforms=[str(cv_ctl) for cv_ctl in self.cv_ctls],
            pinned_transforms=self.def_number,
            primary_axis=(1, 0, 0),
            secondary_axis=(0, 0, 1),
            padded=False,
            parent=parent,
        )

        for i, pinned_transform in enumerate(self.matrix_spline.pinned_transforms):
            self.jnt_pos.append(
                {
                    "obj": pm.PyNode(pinned_transform),
                    "name": self.getName(f"{i}"),
                    "leaf_joint": self.settings["leafJoints"],
                }
            )

    # =====================================================
    # ATTRIBUTES
    # =====================================================
    def addAttributes(self):
        """Setup rig attributes for the component"""
        pass

    # =====================================================
    # OPERATORS
    # =====================================================
    def addOperators(self):
        """Create operators and set the relations for the component rig

        Apply operators, constraints, expressions to the hierarchy.
        In order to keep the code clean and easier to debug,
        we shouldn't create any new object in this method.

        """
        pass

    # =====================================================
    # CONNECTOR
    # =====================================================

    def setRelation(self):
        """Set the relation beetween object from guide to rig"""

        self.relatives["root"] = self.cv_ctls[0]
        self.controlRelatives["root"] = self.cv_ctls[0]
        self.jointRelatives["root"] = 0
        for i in range(0, len(self.guide.apos) - 1):
            self.relatives[f"{i}_cv"] = self.cv_ctls[-1]
            self.controlRelatives[f"{i}_cv"] = self.cv_ctls[-1]
            self.jointRelatives[f"{i}_cv"] = i + 1
        self.relatives[f"{(len(self.guide.apos) - 1)}_cv"] = self.cv_ctls[-1]
        self.controlRelatives[f"{(len(self.guide.apos) - 1)}_cv"] = self.cv_ctls[-1]
        self.jointRelatives[f"{(len(self.guide.apos) - 1)}_cv"] = len(self.guide.apos) - 1
