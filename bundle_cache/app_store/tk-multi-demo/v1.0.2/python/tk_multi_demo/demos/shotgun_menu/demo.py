# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk.platform.qt import QtCore, QtGui

# import the shotgun_menus module from the qtwidgets framework
shotgun_menus = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_menus")


class ShotgunMenuDemo(QtGui.QWidget):
    """
    Demonstrates the use of the the ShotgunMenu class available in the
    tk-frameworks-qtwidgets framework.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(ShotgunMenuDemo, self).__init__(parent)

        # --- build a shotgun menu

        sg_menu = shotgun_menus.ShotgunMenu(self)
        submenu = shotgun_menus.ShotgunMenu(self)
        submenu.setTitle("Submenu")

        # create some dummy actions
        action1 = QtGui.QAction("Action 1", self)
        action2 = QtGui.QAction("Action 2", self)
        action3 = QtGui.QAction("Action 3", self)
        action4 = QtGui.QAction("Action 4", self)

        # add a group of actions to the top-level menu
        sg_menu.add_group([action1, action2, submenu], "Menu Actions")

        # add some actions to the sub menu
        submenu.add_group([action3, action4], "Submenu Actions")

        # a button to trigger the menu
        sg_menu_button = QtGui.QPushButton("ShotgunMenu")
        sg_menu_button.setFixedWidth(100)
        sg_menu_button.clicked.connect(
            lambda: sg_menu.exec_(QtGui.QCursor.pos())
        )
        sg_menu_button.setObjectName("sg_menu_button")

        # help label
        doc = QtGui.QLabel("Click the button to show the menu.")
        doc.setAlignment(QtCore.Qt.AlignCenter)

        # lay out and align the widgets
        layout = QtGui.QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(doc)
        layout.addSpacing(8)
        layout.addWidget(sg_menu_button)
        layout.addStretch()

        layout.setAlignment(sg_menu_button, QtCore.Qt.AlignCenter)
