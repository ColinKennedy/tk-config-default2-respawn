# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk.platform.qt import QtGui, QtCore

from hiero.ui.FnUIProperty import UIPropertyFactory


class CollatingExporterUI(object):
    def __init__(self):
        self._collateTimeProperty = None
        self._collateNameProperty = None

    def populateUI(self, widget, properties=None, cut_support=False):
        """returns a tuple of added uiProperties"""
        if properties is None:
            properties = self._preset.properties()

        layout = QtGui.QFormLayout()

        collateTracksToolTip = """Enable this to include other shots which overlap the sequence time of each shot within the script. Cannot be enabled when Read Node overrides are set."""
        key = "collateTracks"
        value = False
        label = "Collate Shot Timings:"
        self._collateTimeProperty = UIPropertyFactory.create(type(value), key=key, value=value, dictionary=properties, label=label, tooltip=collateTracksToolTip)
        layout.addRow(label, self._collateTimeProperty)

        collateShotNameToolTip = """Enable this to include other shots which have the same name in the Nuke script. Cannot be enabled when Read Node overrides are set."""
        key = "collateShotNames"
        value = False
        label = "Collate Shot Name:"
        self._collateNameProperty = UIPropertyFactory.create(type(value), key=key, value=value, dictionary=properties, label=label, tooltip=collateShotNameToolTip)
        layout.addRow(label, self._collateNameProperty)

        if cut_support:
            cut_lbl = QtGui.QLabel(
                "NOTE: Cuts in Shotgun are only created when collate is off."
            )
            color_role = QtGui.QPalette.WindowText
            palette = widget.palette()
            darker_color = palette.color(color_role).darker(150)
            palette.setColor(color_role, darker_color)
            cut_lbl.setPalette(palette)
            layout.addRow(cut_lbl)

        widget.setLayout(layout)
        return (self._collateTimeProperty, self._collateNameProperty)

    def getCollateTime(self):
        return (self._collateTimeProperty._widget.checkState() == QtCore.Qt.Checked)
    def setCollateTime(self, value):
        self._collateTimeProperty._widget.setChecked(value)
    collateTime = property(getCollateTime, setCollateTime)

    def getCollateName(self):
        return (self._collateNameProperty._widget.checkState() == QtCore.Qt.Checked)
    def setCollateName(self, value):
        self._collateNameProperty._widget.setChecked(value)
    collateName = property(getCollateName, setCollateName)
