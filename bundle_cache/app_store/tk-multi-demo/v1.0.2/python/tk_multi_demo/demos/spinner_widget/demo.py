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

# import the spinner_widget module from the qtwidgets framework
spinner_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "spinner_widget")


class SpinnerWidgetDemo(QtGui.QWidget):
    """
    Demonstrates the use of the the SpinnerWidget class available in the
    tk-frameworks-qtwidgets framework.
    """

    def __init__(self, parent=None):
        """
        Initialize the widget instance.
        """

        # call the base class init
        super(SpinnerWidgetDemo, self).__init__(parent)

        # create the spinner
        spinner = spinner_widget.SpinnerWidget(self)
        spinner.hide()

        # add some geometry so it will show up
        spinner.setFixedSize(QtCore.QSize(100, 100))

        # create some buttons to demo the methods
        start_spinner = QtGui.QPushButton("spinner.show()")
        start_spinner.clicked.connect(spinner.show)

        stop_spinner = QtGui.QPushButton("spinner.hide()")
        stop_spinner.clicked.connect(spinner.hide)

        # ---- layout section ----

        # set up a horizontal layout for the spinner
        spinner_layout = QtGui.QHBoxLayout()
        spinner_layout.addStretch()
        spinner_layout.addWidget(spinner)
        spinner_layout.addStretch()

        # set up a horizontal layout for the buttons
        button_layout = QtGui.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(start_spinner)
        button_layout.addWidget(stop_spinner)
        button_layout.addStretch()

        # lay out the widgets
        layout = QtGui.QVBoxLayout(self)
        layout.setSpacing(20)
        layout.addLayout(button_layout)
        layout.addLayout(spinner_layout)
        layout.addStretch()

