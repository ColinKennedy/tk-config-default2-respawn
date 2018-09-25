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

# import the activity_stream module from the qtwidgets framework
activity_stream = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "activity_stream")

# import the task manager from shotgunutils framework
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager")


class ActivityStreamWidgetDemo(QtGui.QWidget):
    """
    Demos the ActivityStreamWidget from the qtwidgets frameworks.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(ActivityStreamWidgetDemo, self).__init__(parent)

        # get a handle on the current toolkit bundle (the demo app).
        self._app = sgtk.platform.current_bundle()

        # create a background task manager for the widget to use
        self._bg_task_manager = task_manager.BackgroundTaskManager(self)

        # create an instance of the ActivityStreamWidget and then give it the
        # task manager instance.
        self._activity_stream = activity_stream.ActivityStreamWidget(self)
        self._activity_stream.set_bg_task_manager(self._bg_task_manager)

        # this call is specific to the demo app. it tries to return an entity
        # to best illustrate the features of these widgets (i.e. an instance of
        # the supplied entity type that has some activity).
        demo_entity = self._app.get_demo_entity("Project")
        if not demo_entity:
            raise Exception("Could not find suitable entity for this demo!")

        # tell the activity stream to load the entity
        self._activity_stream.load_data(demo_entity)

        # allow screenshots for note entry
        self._activity_stream.allow_screenshots = True

        # show the button to navigate to SG
        self._activity_stream.show_sg_stream_button = True

        # show 'play' buttons on playable versions.
        self._activity_stream.version_items_playable = True

        # connect signals
        self._activity_stream.playback_requested.connect(
            self._on_playback_requested)

        info_lbl = QtGui.QLabel(
            "<strong>LIVE DEMO</strong>: If you click the checkmark to submit "
            "a note, you will attach a new Note to the project in Shotgun. "
            "Just a heads up in case you want to clean up afterward."
        )
        info_lbl.setWordWrap(True)

        # layout the UI
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(info_lbl)
        layout.addWidget(self._activity_stream)

    def destroy(self):
        """
        Clean up the object when deleted.
        """
        self._bg_task_manager.shut_down()
        self._activity_stream.destroy()

    def _on_playback_requested(self, version):
        """A Version was clicked in the stream. Open it up in SG."""

        # build a url for this version
        sg_url = "%s/detail/Version/%d" % (self._app.sgtk.shotgun_url, version["id"])

        # open the url in the default browser
        QtGui.QDesktopServices.openUrl(sg_url)
