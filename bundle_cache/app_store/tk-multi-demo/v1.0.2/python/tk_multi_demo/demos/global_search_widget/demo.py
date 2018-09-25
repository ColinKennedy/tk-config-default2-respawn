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

# import the global_search_widget module from the qtwidgets framework
global_search_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "global_search_widget")

# import the task manager from shotgunutils framework
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager")


class GlobalSearchWidgetDemo(QtGui.QWidget):
    """
    Demonstrates the use of the the GlobalSearchWidget class available in the
    tk-frameworks-qtwidgets framework.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(GlobalSearchWidgetDemo, self).__init__(parent)

        # create a bg task manager for pulling data from SG
        self._bg_task_manager = task_manager.BackgroundTaskManager(self)

        # create the widget
        search_widget = global_search_widget.GlobalSearchWidget(self)

        # give the search widget a handle on the task manager
        search_widget.set_bg_task_manager(self._bg_task_manager)

        # set the entity types to search through (this is also the default dict)
        search_widget.set_searchable_entity_types(
            {
                "Asset": [],
                "Shot": [],
                "Task": [],
                # only active users
                "HumanUser": [["sg_status_list", "is", "act"]],
                "Group": [],
                # only active users
                "ClientUser": [["sg_status_list", "is", "act"]],
                "ApiUser": [],
                "Version": [],
                "PublishedFile": [],
            }
        )

        # display some instructions
        info_lbl = QtGui.QLabel(
            "Click in the widget and type to search for Shotgun entities. You "
            "will need to type at least 3 characters before the search begins."
        )

        # create a label to show when an entity is activated
        self._activated_label = QtGui.QLabel()
        self._activated_label.setWordWrap(True)
        self._activated_label.setStyleSheet(
            """
            QLabel {
                color: #18A7E3;
            }
            """
        )

        # lay out the UI
        layout = QtGui.QVBoxLayout(self)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addWidget(info_lbl)
        layout.addWidget(search_widget)
        layout.addWidget(self._activated_label)
        layout.addStretch()

        # connect the entity activated singal
        search_widget.entity_activated.connect(self._on_entity_activated)

    def destroy(self):
        """Clean up the object when deleted."""
        self._bg_task_manager.shut_down()

    def _on_entity_activated(self, entity_type, entity_id, entity_name):
        """Handle entity activated."""

        self._activated_label.setText(
            "<strong>%s</strong> '%s' with id <tt>%s</tt> activated" % (
                entity_type, entity_name, entity_id)
        )





