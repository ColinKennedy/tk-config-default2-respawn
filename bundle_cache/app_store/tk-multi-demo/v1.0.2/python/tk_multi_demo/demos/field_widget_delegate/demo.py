# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os

import sgtk
from sgtk.platform.qt import QtCore, QtGui

from .ui import resources_rc

# import the shotgun_fields module from the framework
shotgun_fields = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_fields")

# import the shotgun_globals module from shotgunutils framework
shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals")

# import the shotgun_model module from shotgunutils framework
shotgun_model = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_model")

# import the views module from qtwidgets framework
views = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "views")


class FieldWidgetDelegateDemo(QtGui.QWidget):
    """
    This widget shows a form for editing fields on an entity.
    """

    def __init__(self, parent=None):
        """
        Initialize the widget.
        """

        # call the base class init
        super(FieldWidgetDelegateDemo, self).__init__(parent)

        # the fields manager is used to query which fields are supported
        # for display. it can also be used to find out which fields are
        # visible to the user and editable by the user. the fields manager
        # needs time to initialize itself. once that's done, the widgets can
        # begin to be populated.
        self._fields_manager = shotgun_fields.ShotgunFieldManager(self)
        self._fields_manager.initialized.connect(self._populate_ui)
        self._fields_manager.initialize()

    def _populate_ui(self):
        """
        The fields manager has been initialized. Now we can requests some
        widgets to use in the UI.
        :return:
        """

        entity_type = "Project"

        # get a list of fields for the entity type
        fields = shotgun_globals.get_entity_fields(entity_type)

        fields = [
            "image",
            "name",
            "sg_description",
        ]

        # make sure the fields list only includes editable fields
        fields = [f for f in fields
                  if shotgun_globals.field_is_editable(entity_type, f)]

        # make sure the fields are supported by the fields manager
        fields = self._fields_manager.supported_fields(entity_type, fields)

        # we'll display all the fields we're querying in the model
        columns = fields

        # since we've filtered out only editable fields, we'll make those
        # editable within the model
        editable_columns = columns

        # ---- Here we create a ShotgunModel and a ShotgunTableView. The
        #      ShotgunTableView will automatically create delegates for the
        #      columns defined in the model, so you don't have to manually
        #      create delegates yourself.

        auto_delegate_lbl = QtGui.QLabel(
            "A <tt>ShotgunTableView</tt> with auto-assigned field delegates:"
        )

        # create the table view
        self._auto_delegate_table = views.ShotgunTableView(self._fields_manager,
            parent=self)
        self._auto_delegate_table.horizontalHeader().setStretchLastSection(True)

        # setup the model
        self._sg_model = shotgun_model.SimpleShotgunModel(self)
        self._sg_model.load_data(entity_type, fields=fields, columns=columns,
                                 editable_columns=editable_columns)
        self._auto_delegate_table.setModel(self._sg_model)

        # the sg model's first column always includes the entity code and
        # thumbnail. hide that column
        self._auto_delegate_table.hideColumn(0)

        # ---- Here we create our own QStandardItemModel and manually assign
        #      delegates to it. This is useful if you would like to build an
        #      interface to enter data that will eventually be used to create
        #      or update Shotgun entities.

        manual_delegate_lbl = QtGui.QLabel(
            "A Standard <tt>QTableView</tt> with manually-assigned field delegates:"
        )

        self._manual_delegate_table = QtGui.QTableView(self)
        self._manual_delegate_table.horizontalHeader().setStretchLastSection(True)

        # get delegates for each of the columns to display
        image_delegate = self._fields_manager.create_generic_delegate(
            entity_type, "image", self._manual_delegate_table)
        name_delegate = self._fields_manager.create_generic_delegate(
            entity_type, "name", self._manual_delegate_table)
        desc_delegate = self._fields_manager.create_generic_delegate(
            entity_type, "sg_description", self._manual_delegate_table)

        # tell the delegates to get/set data via the display role rather than
        # the default SG model's associated data role. This allows the delegate
        # to be used with non-SG models.
        for delegate in [image_delegate, name_delegate, desc_delegate]:
            delegate.data_role = QtCore.Qt.DisplayRole

        # assign the delegates to the table columns
        self._manual_delegate_table.setItemDelegateForColumn(0, image_delegate)
        self._manual_delegate_table.setItemDelegateForColumn(1, name_delegate)
        self._manual_delegate_table.setItemDelegateForColumn(2, desc_delegate)

        self._standard_model = QtGui.QStandardItemModel(3, 3, self)
        self._standard_model.setHorizontalHeaderLabels(
            ["Thumbnail", "Name", "Description"])

        thumbnail_item = QtGui.QStandardItem()
        thumbnail_item.setData(
            QtGui.QPixmap( ":/tk_multi_demo_field_widget_delegate/project_1.png"),
            image_delegate.data_role
        )

        self._standard_model.insertRow(
            0,
            [
                thumbnail_item,
                QtGui.QStandardItem("New Project"),
                QtGui.QStandardItem("This is a project that could be created."),
            ]
        )
        self._standard_model.insertRow(
            1,
            [
                QtGui.QStandardItem(
                    os.path.join(os.path.dirname(__file__), "resources", "project_2.png")
                ),
                QtGui.QStandardItem("New Project2"),
                QtGui.QStandardItem("Another project example description."),
            ]
        )
        self._manual_delegate_table.setModel(self._standard_model)

        help_lbl = QtGui.QLabel(
            "* Double click fields to modify values <strong>(changes will not be saved)</strong>"
        )

        # and layout the dialog
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(auto_delegate_lbl)
        layout.addWidget(self._auto_delegate_table)
        layout.addWidget(manual_delegate_lbl)
        layout.addWidget(self._manual_delegate_table)
        layout.addWidget(help_lbl)
        self.setLayout(layout)

