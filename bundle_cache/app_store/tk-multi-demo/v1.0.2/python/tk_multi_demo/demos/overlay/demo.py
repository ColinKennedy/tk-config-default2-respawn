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

# import the overlay module from the qtwidgets framework
overlay = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "overlay_widget")


class OverlayDemo(QtGui.QWidget):
    """
    Demonstrates the use of the the overlay widget available in the
    tk-frameworks-qtwidgets framework.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(OverlayDemo, self).__init__(parent)

        # setup a dummy widget to cover with the overlay
        my_label = QtGui.QLabel(
            "This is a label widget with an <tt>OverlayWidget</tt> "
            "parented to it. When shown,<br>the overlay will cover this label "
            "and display a message, error, or pixmap.<br><br><b>Click the "
            "buttons below to simulate calling the overlay's methods.<b>"
        )
        my_label.setWordWrap(True)
        my_label.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        my_label.setStyleSheet("border: 1px solid palette(base);")

        # create the overlay and parent it to the widget it should sit on top of
        overlay_widget = overlay.ShotgunOverlayWidget(my_label)

        # ---- create some buttons to demo the methods

        # shows the overlay widget and starts the spinner. typically this would
        # be called just before starting a long/blocking process
        start_spin = OverlayButton("start_spin()")
        start_spin.clicked.connect(overlay_widget.start_spin)

        # shows a given message in the overlay
        show_message = OverlayButton("show_message()")
        show_message.clicked.connect(
            lambda: overlay_widget.show_message(
                "Showing this message in the overlay widget.\n"
                "The underlying label is now covered by the overlay."
            )
        )

        # shows a pixmap in the overlay
        show_message_pixmap = OverlayButton("show_message_pixmap()")
        show_message_pixmap.clicked.connect(
            lambda: overlay_widget.show_message_pixmap(
                QtGui.QPixmap(":/tk_multi_demo_overlay/toolkit_icon.png")
            )
        )

        # shows a given error message in the overlay
        show_error_message = OverlayButton("show_error_message()")
        show_error_message.clicked.connect(
            lambda: overlay_widget.show_error_message(
                (
                 "Showing this error message in the overlay widget.\nNote the "
                 "show_message() and show_message_pixmap() calls won't work "
                 "when this is displayed."
                )
            )
        )

        # hides the overlay
        hide = OverlayButton("hide()")
        hide.clicked.connect(overlay_widget.hide)

        # lay out and align the widgets
        button_layout = QtGui.QHBoxLayout()
        button_layout.addWidget(start_spin)
        button_layout.addWidget(show_message)
        button_layout.addWidget(show_message_pixmap)
        button_layout.addWidget(show_error_message)
        button_layout.addWidget(hide)

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(my_label)
        layout.addLayout(button_layout)

class OverlayButton(QtGui.QPushButton):
    # a styled wrapper class
    pass
