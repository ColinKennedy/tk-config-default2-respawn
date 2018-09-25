# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'snapshot_history_form.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.2
#
# WARNING! All changes made in this file will be lost!

from tank.platform.qt import QtCore, QtGui

class Ui_SnapshotHistoryForm(object):
    def setupUi(self, SnapshotHistoryForm):
        SnapshotHistoryForm.setObjectName("SnapshotHistoryForm")
        SnapshotHistoryForm.resize(541, 735)
        self.verticalLayout = QtGui.QVBoxLayout(SnapshotHistoryForm)
        self.verticalLayout.setSpacing(-1)
        self.verticalLayout.setContentsMargins(12, 12, 12, 12)
        self.verticalLayout.setObjectName("verticalLayout")
        self.header_frame = QtGui.QFrame(SnapshotHistoryForm)
        self.header_frame.setStyleSheet("#header_frame {\n"
"border-style: solid;\n"
"border-radius: 3;\n"
"border-width: 1;\n"
"border-color: rgb(32,32,32);\n"
"}")
        self.header_frame.setFrameShape(QtGui.QFrame.StyledPanel)
        self.header_frame.setFrameShadow(QtGui.QFrame.Raised)
        self.header_frame.setObjectName("header_frame")
        self.horizontalLayout_3 = QtGui.QHBoxLayout(self.header_frame)
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_3 = QtGui.QLabel(self.header_frame)
        self.label_3.setMinimumSize(QtCore.QSize(80, 80))
        self.label_3.setMaximumSize(QtCore.QSize(80, 80))
        self.label_3.setText("")
        self.label_3.setPixmap(QtGui.QPixmap(":/res/clock.png"))
        self.label_3.setScaledContents(True)
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_3.addWidget(self.label_3)
        self.label = QtGui.QLabel(self.header_frame)
        self.label.setWordWrap(True)
        self.label.setObjectName("label")
        self.horizontalLayout_3.addWidget(self.label)
        self.verticalLayout.addWidget(self.header_frame)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.snapshot_list = SnapshotListView(SnapshotHistoryForm)
        self.snapshot_list.setStyleSheet("#snapshot_list {\n"
"background-color: rgb(255, 128, 0);\n"
"}")
        self.snapshot_list.setObjectName("snapshot_list")
        self.horizontalLayout.addWidget(self.snapshot_list)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.snapshot_btn = QtGui.QPushButton(SnapshotHistoryForm)
        self.snapshot_btn.setObjectName("snapshot_btn")
        self.horizontalLayout_2.addWidget(self.snapshot_btn)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.close_btn = QtGui.QPushButton(SnapshotHistoryForm)
        self.close_btn.setMinimumSize(QtCore.QSize(90, 0))
        self.close_btn.setObjectName("close_btn")
        self.horizontalLayout_2.addWidget(self.close_btn)
        self.restore_btn = QtGui.QPushButton(SnapshotHistoryForm)
        self.restore_btn.setMinimumSize(QtCore.QSize(90, 0))
        self.restore_btn.setObjectName("restore_btn")
        self.horizontalLayout_2.addWidget(self.restore_btn)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.verticalLayout.setStretch(1, 1)

        self.retranslateUi(SnapshotHistoryForm)
        QtCore.QObject.connect(self.close_btn, QtCore.SIGNAL("clicked()"), SnapshotHistoryForm.close)
        QtCore.QMetaObject.connectSlotsByName(SnapshotHistoryForm)

    def retranslateUi(self, SnapshotHistoryForm):
        SnapshotHistoryForm.setWindowTitle(QtGui.QApplication.translate("SnapshotHistoryForm", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("SnapshotHistoryForm", "The list below shows all the snapshots of the currently open work file.  You can go back to a previous version by selecting it and clicking Restore.", None, QtGui.QApplication.UnicodeUTF8))
        self.snapshot_btn.setText(QtGui.QApplication.translate("SnapshotHistoryForm", "New Snapshot...", None, QtGui.QApplication.UnicodeUTF8))
        self.close_btn.setText(QtGui.QApplication.translate("SnapshotHistoryForm", "Close", None, QtGui.QApplication.UnicodeUTF8))
        self.restore_btn.setText(QtGui.QApplication.translate("SnapshotHistoryForm", "Restore", None, QtGui.QApplication.UnicodeUTF8))

from ..snapshot_list_view import SnapshotListView
from . import resources_rc
