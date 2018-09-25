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


class HelpDemo(QtGui.QWidget):
    """
    The default demo used to help users identify the components of the app.
    """

    def __init__(self, parent=None):
        """
        Initialize the widget.
        """

        # call the base class init
        super(HelpDemo, self).__init__(parent)

        # --- add some helper labels with arrows and text...

        summary_lbl = QtGui.QLabel()
        summary_lbl.setPixmap(
            QtGui.QPixmap(":/tk_multi_demo_help/summary_help.png")
        )

        select_lbl = QtGui.QLabel()
        select_lbl.setPixmap(
            QtGui.QPixmap(":/tk_multi_demo_help/select_help.png")
        )

        tabs_lbl = QtGui.QLabel()
        tabs_lbl.setPixmap(
            QtGui.QPixmap(":/tk_multi_demo_help/tabs_help.png")
        )

        # lay out the widgets in the UI
        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(summary_lbl)
        layout.addStretch()
        layout.addWidget(select_lbl)
        layout.addStretch()
        layout.addWidget(tabs_lbl)

        # align the appropriately
        layout.setAlignment(summary_lbl, QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        layout.setAlignment(select_lbl, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        layout.setAlignment(tabs_lbl, QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom)

