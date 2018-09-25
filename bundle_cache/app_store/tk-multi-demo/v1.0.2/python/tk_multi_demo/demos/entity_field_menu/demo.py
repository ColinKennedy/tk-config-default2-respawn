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

# import the shotgun_menus module from the framework
shotgun_menus = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_menus")

# import the shotgun_fields module from the framework
shotgun_fields = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_fields")

# import the task manager from shotgunutils framework
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager")


class EntityFieldMenuDemo(QtGui.QWidget):
    """
    Demonstrates the use of the the EntityFieldMenu class available in the
    tk-frameworks-qtwidgets framework.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(EntityFieldMenuDemo, self).__init__(parent)

        # create a background task manager for each of our components to use
        self._bg_task_manager = task_manager.BackgroundTaskManager(self)

        # --- build an entity field menu

        # build a menu to display Project entity fields
        self._entity_type = "HumanUser"
        self._entity_field_menu = shotgun_menus.EntityFieldMenu(
            self._entity_type,
            self,
            bg_task_manager=self._bg_task_manager
        )

        # a button to trigger the menu
        entity_field_menu_button = QtGui.QPushButton(
            "EntityFieldMenu (%s)" % (self._entity_type,))
        entity_field_menu_button.setObjectName("entity_field_menu_button")

        # show the menu when the button is clicked
        entity_field_menu_button.clicked.connect(
            lambda: self._entity_field_menu.exec_(QtGui.QCursor.pos())
        )

        # help label for the UI
        doc = QtGui.QLabel("Click the button to show the menu.")
        doc.setAlignment(QtCore.Qt.AlignCenter)

        # lay out the widgets
        layout = QtGui.QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(doc)
        layout.addSpacing(8)
        layout.addWidget(entity_field_menu_button)
        layout.addStretch()

        layout.setAlignment(entity_field_menu_button, QtCore.Qt.AlignCenter)

        # the fields manager is used to query which fields are supported
        # for display. it can also be used to find out which fields are
        # visible to the user and editable by the user. the fields manager
        # needs time to initialize itself. once that's done, the widgets can
        # begin to be populated.
        self._fields_manager = shotgun_fields.ShotgunFieldManager(
            self, bg_task_manager=self._bg_task_manager)
        self._fields_manager.initialized.connect(self._populate_ui)
        self._fields_manager.initialize()

    def destroy(self):
        """
        Clean up the object when deleted.
        """
        self._bg_task_manager.shut_down()

    def _populate_ui(self):

        # ---- define a few simple filter methods for use by the menu

        def field_filter(field):
            # Include all fields
            return True

        def checked_filter(field):
            # none of the fields are checked
            return False

        def disabled_filter(field):
            # none of the fields are disabled
            return False

        # attach our filters
        self._entity_field_menu.set_field_filter(field_filter)
        self._entity_field_menu.set_checked_filter(checked_filter)
        self._entity_field_menu.set_disabled_filter(disabled_filter)