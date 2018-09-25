# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'submission_failed_dialog.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from tank.platform.qt import QtCore, QtGui

class Ui_SubmissionFailedDialog(object):
    def setupUi(self, SubmissionFailedDialog):
        SubmissionFailedDialog.setObjectName("SubmissionFailedDialog")
        SubmissionFailedDialog.resize(491, 204)
        self.verticalLayout = QtGui.QVBoxLayout(SubmissionFailedDialog)
        self.verticalLayout.setContentsMargins(20, -1, 20, -1)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_2 = QtGui.QLabel(SubmissionFailedDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_2.sizePolicy().hasHeightForWidth())
        self.label_2.setSizePolicy(sizePolicy)
        self.label_2.setText("")
        self.label_2.setPixmap(QtGui.QPixmap(":/tk-flame-export/failure.png"))
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_3.addWidget(self.label_2)
        self.verticalLayout_3 = QtGui.QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.label_3 = QtGui.QLabel(SubmissionFailedDialog)
        self.label_3.setStyleSheet("QLabel { font-size: 18px; }")
        self.label_3.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label_3.setObjectName("label_3")
        self.verticalLayout_3.addWidget(self.label_3)
        self.status = QtGui.QLabel(SubmissionFailedDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.status.sizePolicy().hasHeightForWidth())
        self.status.setSizePolicy(sizePolicy)
        self.status.setTextFormat(QtCore.Qt.RichText)
        self.status.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.status.setWordWrap(True)
        self.status.setObjectName("status")
        self.verticalLayout_3.addWidget(self.status)
        self.horizontalLayout_3.addLayout(self.verticalLayout_3)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(368, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.submit = QtGui.QPushButton(SubmissionFailedDialog)
        self.submit.setObjectName("submit")
        self.horizontalLayout.addWidget(self.submit)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(SubmissionFailedDialog)
        QtCore.QMetaObject.connectSlotsByName(SubmissionFailedDialog)

    def retranslateUi(self, SubmissionFailedDialog):
        SubmissionFailedDialog.setWindowTitle(QtGui.QApplication.translate("SubmissionFailedDialog", "Shotgun Submission Failed", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("SubmissionFailedDialog", "Something went wrong!", None, QtGui.QApplication.UnicodeUTF8))
        self.status.setText(QtGui.QApplication.translate("SubmissionFailedDialog", "<html><head/><body><p>Either the export was cancelled along the way or an error occurred. No content will be pushed to Shotgun this time. <br/><br/>For more details, please see the log file <span style=\" font-family:\'Courier New,courier\';\">/usr/discreet/log/tk-flame.log</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.submit.setText(QtGui.QApplication.translate("SubmissionFailedDialog", "Ok", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
