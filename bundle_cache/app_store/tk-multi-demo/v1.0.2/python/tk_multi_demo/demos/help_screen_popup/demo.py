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

# make sure the demo's resources are available
from .ui import resources_rc

# import the help_screen module from the framework
help_screen = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "help_screen")


class HelpScreenPopupDemo(QtGui.QWidget):
    """
    Widget to demo the help screens available via qtwidgets frameworks.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(HelpScreenPopupDemo, self).__init__(parent)

        # get a handle on the current toolkit bundle (the demo app). the help
        # screen popup dialog uses this to link back to documentation as well as
        # logging.
        self._app = sgtk.platform.current_bundle()

        # a label with info about how the show method works
        show_lbl = QtGui.QLabel(
            "Click the button below to call the <tt>show_help_screen()</tt> "
            "method. This method accepts a list of <tt>650x400</tt> "
            "<tt>QPixmap</tt>s to display in a series of slides."
        )
        show_lbl.setWordWrap(True)

        # a button to trigger the help screen popup
        show_btn = QtGui.QPushButton("show_help_screen()")
        show_btn.clicked.connect(self._on_show_btn_clicked)

        btn_layout = QtGui.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(show_btn)
        btn_layout.addStretch()

        # lay out the widgets
        layout = QtGui.QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(show_lbl)
        layout.addLayout(btn_layout)
        layout.addStretch()

    def _on_show_btn_clicked(self):
        "Show the help screen popup."

        # build a list of pixmaps
        help_pix = [
            QtGui.QPixmap(":/tk_multi_demo_help_screen_popup/help_screen1.png"),
            QtGui.QPixmap(":/tk_multi_demo_help_screen_popup/help_screen2.png"),
            QtGui.QPixmap(":/tk_multi_demo_help_screen_popup/help_screen3.png"),
            QtGui.QPixmap(":/tk_multi_demo_help_screen_popup/help_screen4.png")
        ]

        # show the help screen!
        help_screen.show_help_screen(self, self._app, help_pix)


