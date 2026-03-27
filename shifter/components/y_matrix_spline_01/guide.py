from functools import partial

from maya.app.general.mayaMixin import MayaQDockWidget, MayaQWidgetDockableMixin  # type: ignore
from mgear.core import pyqt
from mgear.shifter.component import guide
from mgear.vendor.Qt import QtCore, QtWidgets  # type: ignore

from . import settingsUI as sui

# guide info
AUTHOR = "Michael Harmon"
URL = "https://github.com/michaelharmonart/y-rig"
EMAIL = ""
VERSION = [1, 0, 0]
TYPE = "y_matrix_spline_01"
NAME = "spline"
DESCRIPTION = "A spline with a variable number of control points. Interpolates rotation and scale."

##########################################################
# CLASS
##########################################################


class Guide(guide.ComponentGuide):
    """Component Guide Class"""

    compType = TYPE
    compName = NAME
    description = DESCRIPTION

    author = AUTHOR
    url = URL
    email = EMAIL
    version = VERSION

    def postInit(self):
        """Initialize the position for the guide"""

        self.save_transform = ["root", "#_cv"]
        self.addMinMax("#_cv", 2, -1)

    def addObjects(self):
        """Add the Guide Root, blade and locators"""

        self.root = self.addRoot()
        self.locs = self.addLocMulti("#_cv", self.root)

        centers = [self.root]
        centers.extend(self.locs)
        self.dispcrv = self.addDispCurve("crv", centers)
        self.addDispCurve("crvRef", centers, 3)

    def addParameters(self):
        """Add the configurations settings"""

        self.pSegments = self.addParam("segments", "long", 5, 1)
        self.pSplineDegree = self.addParam("spline_degree", "long", 3, 1)
        self.pTweakControls = self.addParam("tweak_controls", "bool", False)
        self.pleafJoints = self.addParam("leafJoints", "bool", False)

        self.pUseIndex = self.addParam("useIndex", "bool", False)
        self.pParentJointIndex = self.addParam("parentJointIndex", "long", -1, None, None)

        # Weight Split Tagging
        self.pWeightSplitTag = self.addParam("weight_split_tag", "bool", True)
        self.pWeightSplitDegree = self.addParam("weight_split_degree", "long", 2, 1)


##########################################################
# Setting Page
##########################################################


class settingsTab(QtWidgets.QDialog, sui.Ui_Form):
    def __init__(self, parent=None):
        super(settingsTab, self).__init__(parent)
        self.setupUi(self)


class componentSettings(MayaQWidgetDockableMixin, guide.componentMainSettings):  # type: ignore
    def __init__(self, parent=None):
        self.toolName = TYPE
        # Delete old instances of the componet settings window.
        pyqt.deleteInstances(self, MayaQDockWidget)

        super(componentSettings, self).__init__(parent=parent)
        self.settingsTab = settingsTab()

        self.setup_componentSettingWindow()
        self.create_componentControls()
        self.populate_componentControls()
        self.create_componentLayout()
        self.create_componentConnections()

    def setup_componentSettingWindow(self):
        self.mayaMainWindow = pyqt.maya_main_window()

        self.setObjectName(self.toolName)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle(TYPE)
        self.resize(350, 350)

    def create_componentControls(self):
        return

    def populate_componentControls(self):
        """Populate Controls

        Populate the controls values from the custom attributes of the
        component.

        """
        # populate tab
        self.tabs.insertTab(1, self.settingsTab, "Component Settings")

        # populate component settings
        self.populateCheck(self.settingsTab.tweak_controls_checkBox, "tweak_controls")
        self.settingsTab.segment_spinBox.setValue(self.root.attr("segments").get())
        self.settingsTab.degree_spinBox.setValue(self.root.attr("spline_degree").get())

    def create_componentLayout(self):
        self.settings_layout = QtWidgets.QVBoxLayout()
        self.settings_layout.addWidget(self.tabs)
        self.settings_layout.addWidget(self.close_button)

        self.setLayout(self.settings_layout)

    def create_componentConnections(self):
        self.settingsTab.segment_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.segment_spinBox, "segments")
        )
        self.settingsTab.degree_spinBox.valueChanged.connect(
            partial(self.updateSpinBox, self.settingsTab.degree_spinBox, "spline_degree")
        )

        self.settingsTab.tweak_controls_checkBox.stateChanged.connect(
            partial(self.updateCheck, self.settingsTab.tweak_controls_checkBox, "tweak_controls")
        )

        self.settingsTab.weight_split_enable_checkBox.stateChanged.connect(
            partial(
                self.updateCheck,
                self.settingsTab.weight_split_enable_checkBox,
                "weight_split_tag",
            )
        )

        self.settingsTab.spline_degree_spinBox.valueChanged.connect(
            partial(
                self.updateSpinBox,
                self.settingsTab.spline_degree_spinBox,
                "weight_split_degree",
            )
        )

    def dockCloseEventTriggered(self):
        pyqt.deleteInstances(self, MayaQDockWidget)
