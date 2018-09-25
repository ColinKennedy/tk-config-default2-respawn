# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'nav_widget_demo.ui'
#
#      by: pyside-uic 0.2.15 running on PySide 1.2.4
#
# WARNING! All changes made in this file will be lost!

from tank.platform.qt import QtCore, QtGui

class Ui_NavigationWidgetDemoUI(object):
    def setupUi(self, NavigationWidgetDemoUI):
        NavigationWidgetDemoUI.setObjectName("NavigationWidgetDemoUI")
        NavigationWidgetDemoUI.resize(349, 338)
        self.verticalLayout = QtGui.QVBoxLayout(NavigationWidgetDemoUI)
        self.verticalLayout.setSpacing(20)
        self.verticalLayout.setObjectName("verticalLayout")
        self.top_layout = QtGui.QGridLayout()
        self.top_layout.setSpacing(8)
        self.top_layout.setObjectName("top_layout")
        self.nav_widget_lbl = QtGui.QLabel(NavigationWidgetDemoUI)
        self.nav_widget_lbl.setStyleSheet("QLabel {\n"
"    color: #999999;\n"
"    font-family: \"Courier\";\n"
"}")
        self.nav_widget_lbl.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.nav_widget_lbl.setObjectName("nav_widget_lbl")
        self.top_layout.addWidget(self.nav_widget_lbl, 0, 0, 1, 1)
        self.nav_widget = NavigationWidget(NavigationWidgetDemoUI)
        self.nav_widget.setObjectName("nav_widget")
        self.top_layout.addWidget(self.nav_widget, 0, 1, 1, 1)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.top_layout.addItem(spacerItem, 0, 2, 1, 1)
        self.breadcrumb_widget_lbl = QtGui.QLabel(NavigationWidgetDemoUI)
        self.breadcrumb_widget_lbl.setStyleSheet("QLabel {\n"
"    color: #999999;\n"
"    font-family: \"Courier\";\n"
"}")
        self.breadcrumb_widget_lbl.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.breadcrumb_widget_lbl.setObjectName("breadcrumb_widget_lbl")
        self.top_layout.addWidget(self.breadcrumb_widget_lbl, 1, 0, 1, 1)
        self.breadcrumb_widget = BreadcrumbWidget(NavigationWidgetDemoUI)
        self.breadcrumb_widget.setObjectName("breadcrumb_widget")
        self.top_layout.addWidget(self.breadcrumb_widget, 1, 1, 1, 2)
        self.top_layout.setColumnStretch(2, 1)
        self.verticalLayout.addLayout(self.top_layout)
        self.tree_view_layout = QtGui.QHBoxLayout()
        self.tree_view_layout.setObjectName("tree_view_layout")
        self.tree_view = QtGui.QTreeView(NavigationWidgetDemoUI)
        self.tree_view.setObjectName("tree_view")
        self.tree_view_layout.addWidget(self.tree_view)
        self.info_lbl = QtGui.QLabel(NavigationWidgetDemoUI)
        self.info_lbl.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.info_lbl.setWordWrap(True)
        self.info_lbl.setObjectName("info_lbl")
        self.tree_view_layout.addWidget(self.info_lbl)
        self.tree_view_layout.setStretch(0, 1)
        self.tree_view_layout.setStretch(1, 1)
        self.verticalLayout.addLayout(self.tree_view_layout)

        self.retranslateUi(NavigationWidgetDemoUI)
        QtCore.QMetaObject.connectSlotsByName(NavigationWidgetDemoUI)

    def retranslateUi(self, NavigationWidgetDemoUI):
        NavigationWidgetDemoUI.setWindowTitle(QtGui.QApplication.translate("NavigationWidgetDemoUI", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.nav_widget_lbl.setText(QtGui.QApplication.translate("NavigationWidgetDemoUI", "NavigationWidget:", None, QtGui.QApplication.UnicodeUTF8))
        self.breadcrumb_widget_lbl.setText(QtGui.QApplication.translate("NavigationWidgetDemoUI", "BreadcrumbWidget:", None, QtGui.QApplication.UnicodeUTF8))
        self.info_lbl.setText(QtGui.QApplication.translate("NavigationWidgetDemoUI", "<html><head/><body><p>Select items in the tree view to the left to see the <span style=\" font-family:\'Courier New,courier\';\">NavigationWidget</span> and <span style=\" font-family:\'Courier New,courier\';\">BreadcrumbWidget</span> above update. Then use the navigation widgets themselves to traverse the selection history in the tree view. Clicking the <span style=\" font-weight:600;\">Home</span> button in the <span style=\" font-family:\'Courier New,courier\';\">NavigationWidget</span> will clear selection.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))

from ..qtwidgets import NavigationWidget, BreadcrumbWidget
