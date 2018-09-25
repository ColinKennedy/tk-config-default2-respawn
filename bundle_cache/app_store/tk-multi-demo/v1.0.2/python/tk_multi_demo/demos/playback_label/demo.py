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
playback_label = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "playback_label")
sg_data = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_data")


class PlaybackLabelDemo(QtGui.QWidget):
    """
    Demonstrates the use of the the PlaybackLabelDemo class available in the
    tk-frameworks-qtwidgets framework.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(PlaybackLabelDemo, self).__init__(parent)

        # construct label object
        label =  playback_label.ShotgunPlaybackLabel(self)

        # get the current bundle
        self._app = sgtk.platform.current_bundle()

        # get Version data from Shotgun. Make sure to include relevant fields.
        # For a Version, this includes:
        #  - image: so you can pass its URL to the thumbnail downloader
        #  - sg_uploaded_movie: which ShotgunPlayBackLabel uses to determine if 
        #    the entity is playable
        fields = ['id', 'code', 'image', 'sg_uploaded_movie']
        #filters = [['image','is_not', None]]
        filters = [['id','is', 6711]]
        version_data = self._app.shotgun.find_one('Version', filters, fields)

        # download the thumbnail for the version
        # TODO: this should be done asynchronously, ShotgunDataRetriever supports this.
        self.__sg_data = sg_data.ShotgunDataRetriever(self)
        self.__sg_data.start()
        thumbnail_path = self.__sg_data.download_thumbnail(version_data['image'], self._app)

        # plug thumbnail into the playback object
        label.setPixmap(thumbnail_path)

        # pass Shotgun data dictionary to the label
        label.set_shotgun_data(version_data)

        # and we can hook it up to other things
        label.playback_clicked.connect(self._on_playback_requested)

        # lay out the widgets
        doc = QtGui.QLabel("You can now click on the thumbnail to play back the Version.")
        doc.setAlignment(QtCore.Qt.AlignCenter)
        layout = QtGui.QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(doc)
        layout.addSpacing(8)
        layout.addWidget(label)
        layout.addStretch()

        layout.setAlignment(label, QtCore.Qt.AlignCenter)

    def _on_playback_requested(self, version):
        """A Version was clicked in the stream. Open it up in SG."""

        # build a url for this version
        sg_url = "%s/detail/Version/%d" % (self._app.sgtk.shotgun_url, version['id'])

        # open the url in the default browser
        QtGui.QDesktopServices.openUrl(sg_url)


    def destroy(self):
        """
        Clean up the object when deleted.
        """

