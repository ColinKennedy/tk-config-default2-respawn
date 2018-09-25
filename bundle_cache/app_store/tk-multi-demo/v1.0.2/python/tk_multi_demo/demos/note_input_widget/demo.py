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
from sgtk.util import get_current_user

# import the note_input_widget module from the qtwidgets framework
note_input_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "note_input_widget")

# import the task manager from shotgunutils framework
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager")


class NoteInputWidgetDemo(QtGui.QWidget):
    """
    Demos the NoteInputWidget from the qtwidgets frameworks.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(NoteInputWidgetDemo, self).__init__(parent)

        # get a handle on the current toolkit bundle (the demo app).
        self._app = sgtk.platform.current_bundle()

        # create a background task manager for the widget to use
        self._bg_task_manager = task_manager.BackgroundTaskManager(self)

        # create an instance of the NoteInputWidget and then give it the task
        # manager.
        self._note_input = note_input_widget.NoteInputWidget(self)
        self._note_input.set_bg_task_manager(self._bg_task_manager)

        # this call is specific to the demo app. it tries to return an entity
        # to best illustrate the features of these widgets (i.e. an instance of
        # the supplied entity type that has some activity).
        demo_entity = self._app.get_demo_entity("HumanUser")
        if not demo_entity:
            raise Exception("Could not find suitable entity for this demo!")

        # tell the input widget which SG entity to attach a note to
        self._note_input.set_current_entity(demo_entity["type"], demo_entity["id"])

        # start the editor open instead of requiring the user to click it
        self._note_input.open_editor()

        # since the widget doesn't work without an entity, make sure the user is
        # aware that this will actually update SG.
        info_lbl = QtGui.QLabel(
            "<strong>LIVE DEMO</strong>: If you click the checkmark to submit "
            "the input, you will attach a new Note to yourself in Shotgun. "
            "Just a heads up in case you want to delete it afterward.<br><br>"
            "It is worth pointing out that Note input on the "
            "<tt>HumanUser</tt> entity in Shotgun is typically not exposed."
        )
        info_lbl.setWordWrap(True)

        # layout the UI
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(info_lbl)
        layout.addWidget(self._note_input)
        layout.addStretch()

    def destroy(self):
        """
        Clean up the object when deleted.
        """
        self._note_input.destroy()
        #self._bg_task_manager.shut_down()


