# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'submission_complete_dialog.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from tank.platform.qt import QtCore, QtGui

class Ui_SubmissionCompleteDialog(object):
    def setupUi(self, SubmissionCompleteDialog):
        SubmissionCompleteDialog.setObjectName("SubmissionCompleteDialog")
        SubmissionCompleteDialog.resize(569, 237)
        self.verticalLayout = QtGui.QVBoxLayout(SubmissionCompleteDialog)
        self.verticalLayout.setContentsMargins(20, -1, 20, -1)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label = QtGui.QLabel(SubmissionCompleteDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setText("")
        self.label.setPixmap(QtGui.QPixmap(":/tk-flame-export/success.png"))
        self.label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label.setObjectName("label")
        self.horizontalLayout_3.addWidget(self.label)
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_3 = QtGui.QLabel(SubmissionCompleteDialog)
        self.label_3.setStyleSheet("QLabel { font-size: 18px; }")
        self.label_3.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label_3.setObjectName("label_3")
        self.verticalLayout_2.addWidget(self.label_3)
        self.status = QtGui.QLabel(SubmissionCompleteDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.status.sizePolicy().hasHeightForWidth())
        self.status.setSizePolicy(sizePolicy)
        self.status.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.status.setWordWrap(True)
        self.status.setObjectName("status")
        self.verticalLayout_2.addWidget(self.status)
        self.horizontalLayout_3.addLayout(self.verticalLayout_2)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(368, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.submit = QtGui.QPushButton(SubmissionCompleteDialog)
        self.submit.setObjectName("submit")
        self.horizontalLayout.addWidget(self.submit)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(SubmissionCompleteDialog)
        QtCore.QMetaObject.connectSlotsByName(SubmissionCompleteDialog)

    def retranslateUi(self, SubmissionCompleteDialog):
        SubmissionCompleteDialog.setWindowTitle(QtGui.QApplication.translate("SubmissionCompleteDialog", "Shotgun Submission Complete", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("SubmissionCompleteDialog", "Submission Complete!", None, QtGui.QApplication.UnicodeUTF8))
        self.status.setText(QtGui.QApplication.translate("SubmissionCompleteDialog", "TextLabel", None, QtGui.QApplication.UnicodeUTF8))
        self.submit.setText(QtGui.QApplication.translate("SubmissionCompleteDialog", "Ok", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
