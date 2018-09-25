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

# import the search_widget module from the qtwidgets framework
search_widget = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "search_widget")


class SearchWidgetDemo(QtGui.QWidget):
    """
    Demonstrates the use of the the SearchWidget class available in the
    tk-frameworks-qtwidgets framework.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(SearchWidgetDemo, self).__init__(parent)

        # create the search widget instance
        search = search_widget.SearchWidget(self)
        search.setFixedWidth(300)

        search.set_placeholder_text("This is the placeholder text...")

        # info
        info_lbl = QtGui.QLabel(
            "Type in the search to see the <tt>search_edited</tt> signal "
            "firing. Then press <strong>Enter</strong> on the keyboard to see "
            "the <tt>search_changed</tt> signal fire."
        )
        info_lbl.setWordWrap(True)

        # signal lbl
        self._signal_lbl = QtGui.QLabel()

        # lay out the UI
        layout = QtGui.QVBoxLayout(self)
        layout.setSpacing(20)
        layout.addStretch()
        layout.addWidget(info_lbl)
        layout.addWidget(search)
        layout.addWidget(self._signal_lbl)
        layout.addStretch()

        # ---- connect the signals

        search.search_edited.connect(self._on_search_edited)
        search.search_changed.connect(self._on_search_changed)

    def _on_search_edited(self, text):
        """Update the signal label."""
        self._signal_lbl.setText(
            "<tt>search_edited</tt>: "
            "<font style='color:#18A7E3;'>%s</font>" % (text,)
        )

    def _on_search_changed(self, text):
        """Update the signal label."""
        self._signal_lbl.setText(
            "<tt>search_changed</tt>: "
            "<font style='color:#18A7E3;'>%s</font>" % (text,)
        )
