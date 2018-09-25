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
from sgtk.platform.constants import SG_STYLESHEET_CONSTANTS

# import the shotgun_fields module from the framework
shotgun_fields = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_fields")

# import the task_manager module from shotgunutils framework
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager")

# import the shotgun_globals module from shotgunutils framework
shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals")


class FieldWidgetsFormDemo(QtGui.QWidget):
    """
    This widget shows a form for editing fields on an entity.
    """

    def __init__(self, parent=None):
        """
        Initialize the widget.
        """

        # call the base class init
        super(FieldWidgetsFormDemo, self).__init__(parent)

        self._bundle = sgtk.platform.current_bundle()

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

    def destroy(self):
        """
        Clean up the object when deleted.
        """
        self._bg_task_manager.shut_down()
        shotgun_globals.unregister_bg_task_manager(self._bg_task_manager)

    def _populate_ui(self):
        """
        The fields manager has been initialized. Now we can requests some
        widgets to use in the UI.
        :return:
        """

        entity_type = "HumanUser"

        # only show visible, editable, supported fields
        human_user_fields = [
            f for f in shotgun_globals.get_entity_fields(entity_type) if
                shotgun_globals.field_is_visible(entity_type, f) and
                shotgun_globals.field_is_editable(entity_type, f)
        ]

        human_user_fields = sorted(
            self._fields_manager.supported_fields(entity_type, human_user_fields))

        # get some info about the current user
        current_user = self._bundle.context.user

        if not current_user:
            layout = QtGui.QVBoxLayout(self)
            layout.addStretch()
            layout.addWidget(
                QtGui.QLabel("FAIL: Could not determine the current user.")
            )
            layout.addStretch()
            return

        # make sure we have all the fields we need for this user
        current_user = self._bundle.shotgun.find_one(
            entity_type,
            [["id", "is", current_user["id"]]],
            fields=human_user_fields,
        )

        form_layout = QtGui.QGridLayout()
        form_layout.setSpacing(4)

        row = 0
        column = 0
        for field in human_user_fields:

            # get the display name for this field
            field_display_name = shotgun_globals.get_field_display_name(
                entity_type, field)

            # get a widget for the entity type and field. supply the current
            # user entity so that the data is populated. by default, this will
            # return an "EDITABLE" widget.
            editable_field_widget = self._fields_manager.create_widget(
                entity_type, field, entity=current_user, parent=self)

            # give the image field widget a minimum size
            if field == "image":
                editable_field_widget.setMinimumSize(QtCore.QSize(64, 64))

            # add the label
            lbl = FieldLabel("%s:" % (field_display_name,))
            form_layout.addWidget(lbl, row, column, QtCore.Qt.AlignRight)

            # add the widget
            form_layout.addWidget(editable_field_widget, row, column+1,
                QtCore.Qt.AlignLeft)

            # listen to the value_changed signal
            editable_field_widget.value_changed.connect(
                lambda f=field_display_name, w=editable_field_widget:
                    self._on_value_changed(f, w)
            )

            row += 1

        form_layout.setRowStretch(row, 10)
        form_layout.setColumnStretch(column+1, 10)

        form_widget = QtGui.QWidget()
        form_widget.setLayout(form_layout)

        scroll_area = QtGui.QScrollArea()
        scroll_area.setWidget(form_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFocusPolicy(QtCore.Qt.NoFocus)

        # add an output box at the bottom of the grid to show what happens as
        # signals are emitted when the widgets are interacted with
        output_lbl = QtGui.QLabel(
            "Interact with the widgets above. Value change signals will be "
            "echo'd below."
        )
        self._output_text = QtGui.QTextEdit()
        self._output_text.setMaximumHeight(100)
        self._output_text.setReadOnly(True)

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(scroll_area)
        layout.addWidget(output_lbl)
        layout.addWidget(self._output_text)

    def _on_value_changed(self, field, widget):
        """
        Respond to the value changed signal.

        :param str field: The name of the field that was edited
        :param widget: The widget whose value changed.
        """
        highlight_color = SG_STYLESHEET_CONSTANTS["SG_HIGHLIGHT_COLOR"]
        self._output_text.append(
            "> <font color='%s'>%s</font> widget value changed to: <B>%s</B>" %
            (highlight_color, field, widget.get_value())
        )

class FieldLabel(QtGui.QLabel):
    """A simple wrapper to allow for easy styling."""
    pass