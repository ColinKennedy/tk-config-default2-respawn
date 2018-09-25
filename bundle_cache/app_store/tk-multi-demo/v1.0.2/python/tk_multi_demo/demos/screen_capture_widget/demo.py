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
from .ui.screen_capture_widget_demo import Ui_ScreenCaptureWidgetDemoUI

# import the shotgun_fields module from the framework
screen_grab = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "screen_grab")

class ScreenCaptureWidgetDemo(QtGui.QWidget):
    """
    Demo of the qtwidgets framework's screen capture capabilities
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(ScreenCaptureWidgetDemo, self).__init__(parent)

        # setup the ui
        self.ui = Ui_ScreenCaptureWidgetDemoUI()
        self.ui.setupUi(self)

        # ---- hook up the buttons to the capture methods

        self.ui.get_desktop_pixmap_btn.clicked.connect(
            self._on_get_desktop_pixmap_btn_clicked)

        self.ui.screen_capture_btn.clicked.connect(
            self._on_screen_capture_btn_clicked)

        self.ui.screen_capture_file_btn.clicked.connect(
            self._on_screen_capture_file_btn_clicked)

    def _on_get_desktop_pixmap_btn_clicked(self):
        """Performs a screen capture on the specified rectangle."""

        # capture the rect and show the results
        rect = QtCore.QRect()
        rect.setLeft(self.ui.left_spin.value())
        rect.setRight(self.ui.right_spin.value())
        rect.setTop(self.ui.top_spin.value())
        rect.setBottom(self.ui.bottom_spin.value())

        self._set_results_pixmap(screen_grab.get_desktop_pixmap(rect))

    def _on_screen_capture_btn_clicked(self):
        """Modally displays the screen capture tool"""

        # capture the screen and show the results
        self._set_results_pixmap(screen_grab.screen_capture())

    def _on_screen_capture_file_btn_clicked(self):
        """Modally display the screen capture tool, saving to a file"""

        # grab the screen to a file (if none supplied it will write to a
        # temp file)
        out_file = screen_grab.screen_capture_file()

        # set the results
        self._set_results_pixmap(QtGui.QPixmap(out_file))

        # display the output path
        self.ui.output_file.setText("Output file: %s" % (out_file,))

    def _set_results_pixmap(self, pixmap):

        # scale to a reasonable size
        pixmap = pixmap.scaled(192, 108,
            QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.ui.results_pixmap.setFixedWidth(pixmap.width())
        self.ui.results_pixmap.setPixmap(pixmap)

        # clear the output file path
        self.ui.output_file.setText("")

