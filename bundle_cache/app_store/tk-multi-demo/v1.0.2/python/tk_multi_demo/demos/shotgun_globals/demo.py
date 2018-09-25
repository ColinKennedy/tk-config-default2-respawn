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

# import the shotgun model module from shotgunutils framework
shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals")

# import the shotgun_fields module from the framework
shotgun_fields = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_fields")

# import the task manager from shotgunutils framework
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager")

# The default entity and field name to display
DEFAULT_ENTITY_TYPE = "HumanUser"
DEFAULT_FIELD_NAME = "name"

class ShotgunGlobalsDemo(QtGui.QWidget):
    """
    Show off the features of the shotgun_globals module in shotgunutils fw.
    """

    def __init__(self, parent=None):
        """
        Initialize the widget.
        """

        # call the base class init
        super(ShotgunGlobalsDemo, self).__init__(parent)

        # the app (current bundle) from the parent widget
        self._app = sgtk.platform.current_bundle()

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

        # --- query some data

        # query the full site schema from shotgun
        self._schema = self._app.shotgun.schema_read()

        # --- build the ui components

        select_lbl = QtGui.QLabel("Select an Entity type from the list:")

        # populate a combo box with all the entity types (the keys)
        self._entity_type_combo = QtGui.QComboBox(self)
        self._entity_type_combo.addItems(sorted(self._schema.keys()))

        field_lbl = QtGui.QLabel("Select a Field name from the list:")

        self._field_name_combo = QtGui.QComboBox(self)
        self._field_name_combo.setSizeAdjustPolicy(
            QtGui.QComboBox.AdjustToContents)

        # get_type_display_name
        type_display_lbl= MethodLabel("get_type_display_name():")
        self._type_display_lbl = ValueLabel()

        # get_field_display_name
        field_display_lbl = MethodLabel("get_field_display_name():")
        self._field_display_lbl = ValueLabel()

        # get_empty_phrase
        empty_phrase_lbl = MethodLabel("get_empty_phrase():")
        self._empty_phrase_lbl = ValueLabel()

        # get_entity_type_icon
        entity_type_icon = MethodLabel("get_entity_type_icon():")
        self._entity_type_icon = ValueLabel()

        # get_entity_type_icon_url
        entity_type_icon_url = MethodLabel("get_entity_type_icon_url():")
        self._entity_type_icon_url = ValueLabel()

        # get_valid_values
        valid_values_lbl = MethodLabel("get_valid_values():")
        self._valid_values_list = QtGui.QListWidget()
        self._valid_values_list.setMaximumHeight(100)

        # field_is_editable
        field_is_editable_lbl = MethodLabel("field_is_editable():")
        self._field_is_editable_lbl = ValueLabel()

        # field_is_visible
        field_is_visible_lbl = MethodLabel("field_is_visible():")
        self._field_is_visible_lbl = ValueLabel()

        # --- layout the components

        row = 0

        layout = QtGui.QGridLayout(self)
        layout.addWidget(select_lbl, row, 0, QtCore.Qt.AlignRight)
        layout.addWidget(self._entity_type_combo, row, 1, QtCore.Qt.AlignLeft)
        row += 1

        layout.addWidget(type_display_lbl, row, 0, QtCore.Qt.AlignRight)
        layout.addWidget(self._type_display_lbl, row, 1, QtCore.Qt.AlignLeft)
        row += 1

        layout.addWidget(entity_type_icon, row, 0, QtCore.Qt.AlignRight)
        layout.addWidget(self._entity_type_icon, row, 1, QtCore.Qt.AlignLeft)
        row += 1

        layout.addWidget(entity_type_icon_url, row, 0, QtCore.Qt.AlignRight)
        layout.addWidget(self._entity_type_icon_url, row, 1, QtCore.Qt.AlignLeft)
        row += 1

        layout.addWidget(field_lbl, row, 0, QtCore.Qt.AlignRight)
        layout.addWidget(self._field_name_combo, row, 1, QtCore.Qt.AlignLeft)
        row += 1

        layout.addWidget(field_display_lbl, row, 0, QtCore.Qt.AlignRight)
        layout.addWidget(self._field_display_lbl, row, 1, QtCore.Qt.AlignLeft)
        row += 1

        layout.addWidget(empty_phrase_lbl, row, 0, QtCore.Qt.AlignRight)
        layout.addWidget(self._empty_phrase_lbl, row, 1, QtCore.Qt.AlignLeft)
        row += 1

        layout.addWidget(valid_values_lbl, row, 0, QtCore.Qt.AlignRight |
            QtCore.Qt.AlignTop)
        layout.addWidget(self._valid_values_list, row, 1, QtCore.Qt.AlignLeft)
        row += 1

        layout.addWidget(field_is_editable_lbl, row, 0, QtCore.Qt.AlignRight)
        layout.addWidget(self._field_is_editable_lbl, row, 1, QtCore.Qt.AlignLeft)
        row += 1

        layout.addWidget(field_is_visible_lbl, row, 0, QtCore.Qt.AlignRight)
        layout.addWidget(self._field_is_visible_lbl, row, 1, QtCore.Qt.AlignLeft)
        row += 1

        # ---- connect some signals

        # handle entity type changes
        self._entity_type_combo.activated[str].connect(
            self._on_entity_type_combo_activated
        )

        # handle field name changes
        self._field_name_combo.activated[str].connect(
            self._on_field_name_combo_activated
        )

        # ---- populate the defaults

        # entity
        entity_type_index = self._entity_type_combo.findText(
            DEFAULT_ENTITY_TYPE)
        if entity_type_index > -1:
            self._entity_type_combo.setCurrentIndex(entity_type_index)
            self._on_entity_type_combo_activated(DEFAULT_ENTITY_TYPE)

        # field
        field_name_index = self._field_name_combo.findText(
            DEFAULT_FIELD_NAME)
        if field_name_index > -1:
            self._field_name_combo.setCurrentIndex(field_name_index)
            self._on_field_name_combo_activated(DEFAULT_FIELD_NAME)

    def destroy(self):
        """
        Clean up the object when deleted.
        """
        self._bg_task_manager.shut_down()

    def _on_entity_type_combo_activated(self, entity_type):
        """
        Handle a new entity type selection.
        """

        # clear the field name combo and repopulate it with the new fields
        self._field_name_combo.clear()
        self._field_name_combo.addItems(
            sorted(self._schema[entity_type].keys())
        )
        self._field_name_combo.adjustSize()

        # --- update the entity-specific method widgets

        # type display
        type_display_name = shotgun_globals.get_type_display_name(entity_type)
        self._type_display_lbl.setText(type_display_name)

        # type icon
        type_icon = shotgun_globals.get_entity_type_icon(entity_type)
        if type_icon:
            self._entity_type_icon.setPixmap(type_icon.pixmap(22, 22))
        else:
            self._entity_type_icon.clear()

        # type icon url
        type_icon_url = shotgun_globals.get_entity_type_icon_url(entity_type)
        self._entity_type_icon_url.setText(type_icon_url)

        self._on_field_name_combo_activated(
            self._field_name_combo.currentText())

    def _on_field_name_combo_activated(self, field_name):
        """
        Handle a new field name selection.
        """

        entity_type = self._entity_type_combo.currentText()

        # --- update the labels for the various methods

        # field display
        field_display_name = shotgun_globals.get_field_display_name(
            entity_type, field_name)
        self._field_display_lbl.setText(field_display_name)

        # empty phrase
        empty_phrase = shotgun_globals.get_empty_phrase(
            entity_type, field_name)
        self._empty_phrase_lbl.setText(empty_phrase)

        # valid values
        self._valid_values_list.clear()
        try:
            valid_values = shotgun_globals.get_valid_values(
                entity_type, field_name)
        except ValueError:
            pass
        else:
            self._valid_values_list.addItems(valid_values)

        # editable
        field_is_editable = shotgun_globals.field_is_editable(
            entity_type, field_name
        )
        self._field_is_editable_lbl.setText(str(field_is_editable))

        # visible
        field_is_visible = shotgun_globals.field_is_visible(
            entity_type, field_name
        )
        self._field_is_visible_lbl.setText(str(field_is_visible))

class MethodLabel(QtGui.QLabel):
    """
    Bare subclass for styling.
    """
    pass

class ValueLabel(QtGui.QLabel):
    """
    Bare subclass for styling.
    """
    pass
