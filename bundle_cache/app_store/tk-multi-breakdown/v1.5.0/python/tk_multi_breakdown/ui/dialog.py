# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'dialog.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from sgtk.platform.qt import QtCore, QtGui

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(490, 618)
        self.verticalLayout = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.browser = SceneBrowserWidget(Dialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.browser.sizePolicy().hasHeightForWidth())
        self.browser.setSizePolicy(sizePolicy)
        self.browser.setObjectName("browser")
        self.verticalLayout.addWidget(self.browser)
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setSpacing(3)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.groupBox = QtGui.QGroupBox(Dialog)
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setSpacing(10)
        self.horizontalLayout_2.setContentsMargins(2, 2, 2, 2)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.chk_green = QtGui.QCheckBox(self.groupBox)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/res/green_bullet.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.chk_green.setIcon(icon)
        self.chk_green.setObjectName("chk_green")
        self.horizontalLayout_2.addWidget(self.chk_green)
        self.chk_red = QtGui.QCheckBox(self.groupBox)
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/res/red_bullet.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.chk_red.setIcon(icon1)
        self.chk_red.setObjectName("chk_red")
        self.horizontalLayout_2.addWidget(self.chk_red)
        self.horizontalLayout_3.addWidget(self.groupBox)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.select_all = QtGui.QPushButton(Dialog)
        self.select_all.setObjectName("select_all")
        self.horizontalLayout_3.addWidget(self.select_all)
        self.update = QtGui.QPushButton(Dialog)
        self.update.setObjectName("update")
        self.horizontalLayout_3.addWidget(self.update)
        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QtGui.QApplication.translate("Dialog", "Scene Breakdown", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Dialog", "Filters:", None, QtGui.QApplication.UnicodeUTF8))
        self.select_all.setText(QtGui.QApplication.translate("Dialog", "Select All Red", None, QtGui.QApplication.UnicodeUTF8))
        self.update.setText(QtGui.QApplication.translate("Dialog", "Update Selected", None, QtGui.QApplication.UnicodeUTF8))

from ..scene_browser import SceneBrowserWidget
from . import resources_rc
