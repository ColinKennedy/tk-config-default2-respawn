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
from sgtk.platform.qt import QtGui


class EngineShowBusyDemo(QtGui.QWidget):
    """
    Widget to demo the `engine.show_busy()` and `engine.clear_busy()` methods.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(EngineShowBusyDemo, self).__init__(parent)

        # a button that will show a busy dialog with a title and some text
        show_btn = QtGui.QPushButton("show_busy(title, details)")
        show_btn.setObjectName("show_busy_dialog_demo_button")
        show_btn.clicked.connect(self._on_show_button_clicked)

        # a button that will clear any displayed busy dialog
        clear_btn = QtGui.QPushButton("clear_busy()")
        clear_btn.setObjectName("clear_busy_dialog_demo_button")
        clear_btn.clicked.connect(self._on_clear_button_clicked)

        # just add the buttons to a layout
        layout = QtGui.QHBoxLayout(self)
        layout.addStretch()
        layout.addWidget(show_btn)
        layout.addWidget(clear_btn)
        layout.addStretch()

    def _on_show_button_clicked(self):
        """
        Callback for when the show button is clicked
        """

        # get a handle on the current engine
        engine = sgtk.platform.current_engine()

        # also available globally via `sgtk.platform.engine.show_global_busy()`
        # if you don't have a handle on the current engine.
        engine.show_busy(
            "Example: Something is Taking a Long Time...",
            "Here is some description of why this is taking so long. " +
            "Click the <tt>clear_busy()</tt> button or anywhere in this " +
            "dialog to clear it."
        )

    def _on_clear_button_clicked(self):
        """
        Callback for when the clear button is clicked
        """

        # get a handle on the current engine
        engine = sgtk.platform.current_engine()
        engine.clear_busy()


