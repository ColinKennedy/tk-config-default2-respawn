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

# import the shotgun_fields module from the qtwidgets framework
shotgun_fields = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_fields")

# import the shotgun_globals module from the qtwidgets framework
shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals")

# import the shotgun_model module from the qtwidgets framework
shotgun_model = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_model")

# import the task_manager module from shotgunutils framework
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager")

# import the shotgun_fields module from the qtwidgets framework
views = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "views")

# ensure our icon resources are imported
from .ui import resources_rc

# importing this will register the class with the fields manager
from .favorite_widget import MyProjectFavoritesWidget


class CustomFieldWidgetDemo(QtGui.QWidget):
    """
    Demonstrates how to override one of the default Shotgun field widgets.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(CustomFieldWidgetDemo, self).__init__(parent)

        # create a background task manager for each of our components to use
        self._bg_task_manager = task_manager.BackgroundTaskManager(self)

        # the fields manager is used to query which fields are supported
        # for display. it can also be used to find out which fields are
        # visible to the user and editable by the user. the fields manager
        # needs time to initialize itself. once that's done, the widgets can
        # begin to be populated.
        self._fields_manager = shotgun_fields.ShotgunFieldManager(
            self, bg_task_manager=self._bg_task_manager)
        self._fields_manager.initialized.connect(self._populate_ui)
        self._fields_manager.initialize()

    def _populate_ui(self):
        """Populate the ui after the fields manager has been initialized."""

        # create a SG model to retrieve our data
        self._model = shotgun_model.SimpleShotgunModel(
            self, self._bg_task_manager)

        # and a table view to display our SG model
        table_view = views.ShotgunTableView(self._fields_manager, self)
        table_view.horizontalHeader().setStretchLastSection(True)

        # the fields to query
        fields = [
            "image",
            "name",
            "current_user_favorite",
            "sg_description",
        ]

        # load the data into the model
        self._model.load_data(
            "Project",
            fields=fields,
            limit=10,
            columns=fields,
            editable_columns=["current_user_favorite"]
        )

        # now apply the model to the table view
        table_view.setModel(self._model)
        table_view.hideColumn(0)

        # info label
        info_lbl = QtGui.QLabel(
            "The table below is showing a list of all <strong>Project</strong> "
            "entities for the current SG site with a custom field widget in "
            "the <strong>Favorite</strong> column. The default widget is a "
            "standard <tt>QtGui.QCheckBox</tt>. Here you'll see a subclass of "
            "<tt>QCheckBox</tt> that uses images as the check indicator. This "
            "is a simple example of how you can override a field widget for "
            "a specific field on a specific entity.<br><br>"
            "Double click a cell in the <strong>Favorite</strong> to make the "
            "entry editable. Then click on the icon to toggle the favorite "
            "value. Note, this is not a live demo. SG will not be updated."
        )
        info_lbl.setWordWrap(True)

        # lay out the widgets
        layout = QtGui.QVBoxLayout(self)
        layout.setSpacing(20)
        layout.addWidget(info_lbl)
        layout.addWidget(table_view)

    def destroy(self):
        """
        Clean up the object when deleted.
        """
        self._bg_task_manager.shut_down()
        shotgun_globals.unregister_bg_task_manager(self._bg_task_manager)

