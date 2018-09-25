# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'batch_render_dialog.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from tank.platform.qt import QtCore, QtGui

class Ui_BatchRenderDialog(object):
    def setupUi(self, BatchRenderDialog):
        BatchRenderDialog.setObjectName("BatchRenderDialog")
        BatchRenderDialog.resize(352, 398)
        self.verticalLayout = QtGui.QVBoxLayout(BatchRenderDialog)
        self.verticalLayout.setContentsMargins(20, 20, 20, -1)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_2 = QtGui.QLabel(BatchRenderDialog)
        self.label_2.setText("")
        self.label_2.setPixmap(QtGui.QPixmap(":/tk-flame-export/batch_render_splash.png"))
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.comments = QtGui.QPlainTextEdit(BatchRenderDialog)
        self.comments.setMinimumSize(QtCore.QSize(300, 100))
        self.comments.setObjectName("comments")
        self.verticalLayout.addWidget(self.comments)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setSpacing(4)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(368, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.cancel = QtGui.QPushButton(BatchRenderDialog)
        self.cancel.setObjectName("cancel")
        self.horizontalLayout.addWidget(self.cancel)
        self.submit = QtGui.QPushButton(BatchRenderDialog)
        self.submit.setObjectName("submit")
        self.horizontalLayout.addWidget(self.submit)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(BatchRenderDialog)
        QtCore.QMetaObject.connectSlotsByName(BatchRenderDialog)

    def retranslateUi(self, BatchRenderDialog):
        BatchRenderDialog.setWindowTitle(QtGui.QApplication.translate("BatchRenderDialog", "Submit to Shotgun", None, QtGui.QApplication.UnicodeUTF8))
        self.cancel.setText(QtGui.QApplication.translate("BatchRenderDialog", "Skip", None, QtGui.QApplication.UnicodeUTF8))
        self.submit.setText(QtGui.QApplication.translate("BatchRenderDialog", "Send to Shotgun Review", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
