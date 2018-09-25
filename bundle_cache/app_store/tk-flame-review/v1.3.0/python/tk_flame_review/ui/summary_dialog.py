# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'summary_dialog.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from tank.platform.qt import QtCore, QtGui

class Ui_SummaryDialog(object):
    def setupUi(self, SummaryDialog):
        SummaryDialog.setObjectName("SummaryDialog")
        SummaryDialog.resize(501, 175)
        self.verticalLayout = QtGui.QVBoxLayout(SummaryDialog)
        self.verticalLayout.setContentsMargins(20, -1, 20, -1)
        self.verticalLayout.setObjectName("verticalLayout")
        self.stackedWidget = QtGui.QStackedWidget(SummaryDialog)
        self.stackedWidget.setObjectName("stackedWidget")
        self.page = QtGui.QWidget()
        self.page.setObjectName("page")
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.page)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label = QtGui.QLabel(self.page)
        self.label.setText("")
        self.label.setPixmap(QtGui.QPixmap(":/tk-flame-review/submission_complete.png"))
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.stackedWidget.addWidget(self.page)
        self.page_2 = QtGui.QWidget()
        self.page_2.setObjectName("page_2")
        self.verticalLayout_3 = QtGui.QVBoxLayout(self.page_2)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.label_2 = QtGui.QLabel(self.page_2)
        self.label_2.setText("")
        self.label_2.setPixmap(QtGui.QPixmap(":/tk-flame-review/submission_failed.png"))
        self.label_2.setObjectName("label_2")
        self.verticalLayout_3.addWidget(self.label_2)
        self.stackedWidget.addWidget(self.page_2)
        self.verticalLayout.addWidget(self.stackedWidget)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(368, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.submit = QtGui.QPushButton(SummaryDialog)
        self.submit.setObjectName("submit")
        self.horizontalLayout.addWidget(self.submit)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(SummaryDialog)
        self.stackedWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(SummaryDialog)

    def retranslateUi(self, SummaryDialog):
        SummaryDialog.setWindowTitle(QtGui.QApplication.translate("SummaryDialog", "Submit to Shotgun", None, QtGui.QApplication.UnicodeUTF8))
        self.submit.setText(QtGui.QApplication.translate("SummaryDialog", "Ok", None, QtGui.QApplication.UnicodeUTF8))

from . import resources_rc
