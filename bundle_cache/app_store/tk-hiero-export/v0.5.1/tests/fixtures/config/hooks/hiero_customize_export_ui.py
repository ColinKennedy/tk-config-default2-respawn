# Copyright (c) 2018 Shotgun Software Inc.
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

HookBaseClass = sgtk.get_hook_baseclass()


class HieroCustomizeExportUI(HookBaseClass):
    def create_shot_processor_widget(self, parent_widget):
        widget = QtGui.QGroupBox("My Custom Properties", parent_widget)
        widget.setLayout(QtGui.QFormLayout())
        return widget

    def get_shot_processor_ui_properties(self):
        return [
            dict(
                label="Custom one:",
                name="custom_one",
                value=True,
                tooltip="Custom one tooltip",
            )
        ]

    def set_shot_processor_ui_properties(self, widget, properties):
        layout = widget.layout()
        for label, prop in properties.iteritems():
            layout.addRow(label, prop)

    def create_transcode_exporter_widget(self, parent_widget):
        widget = QtGui.QGroupBox("My Custom Properties", parent_widget)
        widget.setLayout(QtGui.QFormLayout())
        return widget

    def get_transcode_exporter_ui_properties(self):
        return [
            dict(
                label="Custom two:",
                name="custom_two",
                value=True,
                tooltip="Custom two tooltip",
            )
        ]

    def set_transcode_exporter_ui_properties(self, widget, properties):
        layout = widget.layout()
        for label, prop in properties.iteritems():
            layout.addRow(label, prop)

    def create_audio_exporter_widget(self, parent_widget):
        widget = QtGui.QGroupBox("My Custom Properties", parent_widget)
        widget.setLayout(QtGui.QFormLayout())
        return widget

    def get_audio_exporter_ui_properties(self):
        return [
            dict(
                label="Custom three:",
                name="custom_three",
                value=True,
                tooltip="Custom three tooltip",
            )
        ]

    def set_audio_exporter_ui_properties(self, widget, properties):
        layout = widget.layout()
        for label, prop in properties.iteritems():
            layout.addRow(label, prop)

    def create_nuke_shot_exporter_widget(self, parent_widget):
        widget = QtGui.QGroupBox("My Custom Properties", parent_widget)
        widget.setLayout(QtGui.QFormLayout())
        return widget

    def get_nuke_shot_exporter_ui_properties(self):
        return [
            dict(
                label="Custom four:",
                name="custom_four",
                value=True,
                tooltip="Custom four tooltip",
            )
        ]

    def set_nuke_shot_exporter_ui_properties(self, widget, properties):
        layout = widget.layout()
        for label, prop in properties.iteritems():
            layout.addRow(label, prop)
