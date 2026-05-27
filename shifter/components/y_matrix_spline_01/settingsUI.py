################################################################################
## Form generated from reading UI file 'settingsUISnnsaC.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from Qt.QtCore import (
    QCoreApplication,
    QMetaObject,
)
from Qt.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
)


class Ui_Form:
    def setupUi(self, Form) -> None:
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(294, 294)
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalSpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.gridLayout.addItem(self.verticalSpacer, 8, 0, 1, 1)

        self.main_formLayout = QFormLayout()
        self.main_formLayout.setObjectName("main_formLayout")
        self.segment_label = QLabel(Form)
        self.segment_label.setObjectName("segment_label")

        self.main_formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.segment_label)

        self.segment_spinBox = QSpinBox(Form)
        self.segment_spinBox.setObjectName("segment_spinBox")
        self.segment_spinBox.setMinimum(1)
        self.segment_spinBox.setMaximum(999)
        self.segment_spinBox.setValue(3)

        self.main_formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.segment_spinBox)

        self.degree_label = QLabel(Form)
        self.degree_label.setObjectName("degree_label")

        self.main_formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.degree_label)

        self.degree_spinBox = QSpinBox(Form)
        self.degree_spinBox.setObjectName("degree_spinBox")
        self.degree_spinBox.setMinimum(1)
        self.degree_spinBox.setMaximum(999)
        self.degree_spinBox.setValue(3)

        self.main_formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.degree_spinBox)

        self.tweak_controls_checkBox = QCheckBox(Form)
        self.tweak_controls_checkBox.setObjectName("tweak_controls_checkBox")
        self.tweak_controls_checkBox.setText(" Tweak Controls")

        self.main_formLayout.setWidget(
            2, QFormLayout.ItemRole.LabelRole, self.tweak_controls_checkBox
        )

        self.gridLayout.addLayout(self.main_formLayout, 0, 0, 1, 1)

        self.weight_split_formLayout = QFormLayout()
        self.weight_split_formLayout.setObjectName("weight_split_formLayout")
        self.weight_split_label = QLabel(Form)
        self.weight_split_label.setObjectName("weight_split_label")

        self.weight_split_formLayout.setWidget(
            3, QFormLayout.ItemRole.SpanningRole, self.weight_split_label
        )

        self.weight_split_enable_label = QLabel(Form)
        self.weight_split_enable_label.setObjectName("weight_split_enable_label")

        self.weight_split_formLayout.setWidget(
            4, QFormLayout.ItemRole.LabelRole, self.weight_split_enable_label
        )

        self.weight_split_enable_checkBox = QCheckBox(Form)
        self.weight_split_enable_checkBox.setObjectName("weight_split_enable_checkBox")
        self.weight_split_enable_checkBox.setChecked(True)

        self.weight_split_formLayout.setWidget(
            4, QFormLayout.ItemRole.FieldRole, self.weight_split_enable_checkBox
        )

        self.spline_degree_label = QLabel(Form)
        self.spline_degree_label.setObjectName("spline_degree_label")

        self.weight_split_formLayout.setWidget(
            5, QFormLayout.ItemRole.LabelRole, self.spline_degree_label
        )

        self.spline_degree_spinBox = QSpinBox(Form)
        self.spline_degree_spinBox.setObjectName("spline_degree_spinBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.spline_degree_spinBox.sizePolicy().hasHeightForWidth())
        self.spline_degree_spinBox.setSizePolicy(sizePolicy)
        self.spline_degree_spinBox.setMinimum(1)
        self.spline_degree_spinBox.setMaximum(5)

        self.weight_split_formLayout.setWidget(
            5, QFormLayout.ItemRole.FieldRole, self.spline_degree_spinBox
        )

        self.gridLayout.addLayout(self.weight_split_formLayout, 7, 0, 1, 1)

        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)

    # setupUi

    def retranslateUi(self, Form) -> None:
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.segment_label.setText(QCoreApplication.translate("Form", "Number of Segments", None))
        self.degree_label.setText(QCoreApplication.translate("Form", "Spline Degree", None))
        self.weight_split_label.setText(
            QCoreApplication.translate("Form", "Weight Split Tagging", None)
        )
        # if QT_CONFIG(tooltip)
        self.weight_split_enable_label.setToolTip(
            QCoreApplication.translate(
                "Form",
                "When enabled the component's joints will be tagged to have metadata for automatic skin weight splitting.",
                None,
            )
        )
        # endif // QT_CONFIG(tooltip)
        self.weight_split_enable_label.setText(QCoreApplication.translate("Form", "Enable", None))
        # if QT_CONFIG(tooltip)
        self.weight_split_enable_checkBox.setToolTip(
            QCoreApplication.translate(
                "Form",
                "When enabled the component's joints will be tagged to have metadata for automatic skin weight splitting.",
                None,
            )
        )
        # endif // QT_CONFIG(tooltip)
        self.weight_split_enable_checkBox.setText("")
        # if QT_CONFIG(tooltip)
        self.spline_degree_label.setToolTip(
            QCoreApplication.translate(
                "Form",
                'This corresponds to the degree of the spline used for the skin weight splitting. A higher value will result in a "smoother" weight split. A value of one is a linear spline, 2 quadratic, etc.',
                None,
            )
        )
        # endif // QT_CONFIG(tooltip)
        self.spline_degree_label.setText(QCoreApplication.translate("Form", "Spline Degree", None))
        # if QT_CONFIG(tooltip)
        self.spline_degree_spinBox.setToolTip(
            QCoreApplication.translate(
                "Form",
                'This corresponds to the degree of the spline used for the skin weight splitting. A higher value will result in a "smoother" weight split. A value of one is a linear spline, 2 quadratic, etc.',
                None,
            )
        )


# endif // QT_CONFIG(tooltip)
# retranslateUi
