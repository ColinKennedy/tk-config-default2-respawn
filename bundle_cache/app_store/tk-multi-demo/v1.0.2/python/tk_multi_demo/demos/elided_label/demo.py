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

# import the elided_label module from the qtwidgets framework
elided_label = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "elided_label")


class ElidedLabelDemo(QtGui.QWidget):
    """
    Demonstrates the use of the the ElidedLabel class available in the
    tk-frameworks-qtwidgets framework.
    """

    def __init__(self, parent=None):
        """
        Initialize the widget instance.
        """

        # call the base class init
        super(ElidedLabelDemo, self).__init__(parent)

        # some text to display in the label
        start_text = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque "
            "non posuere lorem. Donec non lobortis mauris. Morbi risus est, "
        )

        # create the label and set the text
        label = elided_label.ElidedLabel()
        label.setText(start_text)

        # a little style to help highlight the label boundaries
        label.setStyleSheet(
            "background: palette(base);"
            "padding: 4px;"
        )

        # ---- add a slider to adjust the width of the label

        slider = QtGui.QSlider()
        slider.setOrientation(QtCore.Qt.Horizontal)
        slider.setMinimum(10)
        slider.setMaximum(600)
        slider.setFocusPolicy(QtCore.Qt.NoFocus)

        # set the initial value
        slider.valueChanged.connect(label.setFixedWidth)
        slider.setValue(295)

        # another label to show instructions in the UI
        doc = QtGui.QLabel("Move the slider to resize the elided label.")
        doc.setAlignment(QtCore.Qt.AlignCenter)

        # lay out the widgets
        layout = QtGui.QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(label)
        layout.addSpacing(8)
        layout.addWidget(slider)
        layout.addWidget(doc)
        layout.addStretch()
