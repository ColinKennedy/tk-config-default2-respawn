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

HookBaseClass = sgtk.get_hook_baseclass()


class HieroCustomizeExportUI(HookBaseClass):
    """
    This class defines methods that can be used to customize the UI of the various
    Shotgun-related exporters. Each processor has its own set of create/get/set
    methods, allowing for customizable UI elements for each type of export.

    Example properties embedded into a custom QGroupBox:

    .. figure:: ./resources/hiero_export_custom_ui.png

    ..

    Creating custom UI elements for the Hiero export app involves three steps:

    - Creating a widget
    - Defining custom properties to add to the associated preset
    - Setting the widget up to display controls for the custom properties
    """
    def create_shot_processor_widget(self, parent_widget):
        """
        Builds and returns a custom widget to be embedded in the parent exporter.
        If a custom widget is returned by this method, it will be added to the
        parent exporter's layout.

        Example Implementation:

        .. code-block:: python

            widget = QtGui.QGroupBox("My Custom Properties", parent_widget)
            widget.setLayout(QtGui.QFormLayout())
            return widget

        :param parent_widget: The parent widget.

        :returns: A custom widget.
        """
        return None

    def get_shot_processor_ui_properties(self):
        """
        Gets a list of property dictionaries describing the custom properties
        required by the custom widget. This method will only be run if the
        associated create widget hook method returns a widget. The dictionaries
        will be turned into property widgets by the app before being passed to
        the associated set properties hook method. The order that the dictionaries
        are returned by this method is maintained when they are passed to the
        associated set hook method.

        Example Implementation:

        .. code-block:: python

            return [
                dict(
                    label="Create Cut:",
                    name="custom_create_cut_bool_property",
                    value=True,
                    tooltip="Create a Cut and CutItems in Shotgun...",
                ),
                dict(
                    label="Head In:",
                    name="custom_head_in_bool_property",
                    value=True,
                    tooltip="Update 'sg_head_in' on the Shot entity.",
                ),
            ]

        :returns: A list of dictionaries.
        :rtype: list
        """
        return []

    def set_shot_processor_ui_properties(self, widget, properties):
        """
        Sets any custom properties described by get_shot_processor_ui_properties
        on the custom widget returned by create_shot_processor_widget. This method
        will only be called if the create method is implemented to return a custom
        widget. The order of the properties within the dictionary passed in is the
        same as the order they're returned in the get properties hook method.

        Example Implementation:

        .. code-block:: python

            layout = widget.layout()
            for label, prop in properties.iteritems():
                layout.addRow(label, prop)

        :param widget: The Qt widget that was created by the associated create
            widget hook method.
        :param OrderedDict properties: A dict containing property widget
            objects, keyed by label, that were constructed from the data
            built by the associated get properties hook method.
        """
        return

    def create_transcode_exporter_widget(self, parent_widget):
        """
        Builds and returns a custom widget to be embedded in the parent exporter.
        If a custom widget is returned by this method, it will be added to the
        parent exporter's layout.

        .. note:: See the :meth:`create_shot_processor_widget` method for
            more detailed documentation.

        :param parent_widget: The parent widget.

        :returns: A custom widget.
        """
        return None

    def get_transcode_exporter_ui_properties(self):
        """
        Gets a list of property dictionaries describing the custom properties
        required by the custom widget. This method will only be run if the
        associated create widget hook method returns a widget. The dictionaries
        will be turned into property widgets by the app before being passed to
        the associated set properties hook method. The order that the dictionaries
        are returned by this method is maintained when they are passed to the
        associated set hook method.

        .. note:: See the :meth:`get_shot_processor_ui_properties` method for
            more detailed documentation.

        :returns: A list of dictionaries.
        :rtype: list
        """
        return []

    def set_transcode_exporter_ui_properties(self, widget, properties):
        """
        Sets any custom properties described by get_transcode_exporter_ui_properties
        on the custom widget returned by create_transcode_exporter_widget. This method
        will only be called if the create method is implemented to return a custom
        widget. The order of the properties within the dictionary passed in is the
        same as the order they're returned in the get properties hook method.

        .. note:: See the :meth:`set_shot_processor_ui_properties` method for
            for an example implementation.

        :param widget: The Qt widget that was created by the associated create
            widget hook method.
        :param OrderedDict properties: A dict containing property widget
            objects, keyed by label, that were constructed from the data
            built by the associated get properties hook method.
        """
        return

    def create_audio_exporter_widget(self, parent_widget):
        """
        Builds and returns a custom widget to be embedded in the parent exporter.
        If a custom widget is returned by this method, it will be added to the
        parent exporter's layout.

        .. note:: See the :meth:`create_shot_processor_widget` method for
            more detailed documentation.

        :param parent_widget: The parent widget.

        :returns: A custom widget.
        """
        return None

    def get_audio_exporter_ui_properties(self):
        """
        Gets a list of property dictionaries describing the custom properties
        required by the custom widget. This method will only be run if the
        associated create widget hook method returns a widget. The dictionaries
        will be turned into property widgets by the app before being passed to
        the associated set properties hook method. The order that the dictionaries
        are returned by this method is maintained when they are passed to the
        associated set hook method.

        .. note:: See the :meth:`get_shot_processor_ui_properties` method for
            more detailed documentation.

        :returns: A list of dictionaries.
        :rtype: list
        """
        return []

    def set_audio_exporter_ui_properties(self, widget, properties):
        """
        Sets any custom properties described by get_audio_exporter_ui_properties
        on the custom widget returned by create_audio_exporter_widget. This method
        will only be called if the create method is implemented to return a custom
        widget. The order of the properties within the dictionary passed in is the
        same as the order they're returned in the get properties hook method.

        .. note:: See the :meth:`set_shot_processor_ui_properties` method for
            for an example implementation.

        :param widget: The Qt widget that was created by the associated create
            widget hook method.
        :param OrderedDict properties: A dict containing property widget
            objects, keyed by label, that were constructed from the data
            built by the associated get properties hook method.
        """
        return

    def create_nuke_shot_exporter_widget(self, parent_widget):
        """
        Builds and returns a custom widget to be embedded in the parent exporter.
        If a custom widget is returned by this method, it will be added to the
        parent exporter's layout.

        .. note:: See the :meth:`create_shot_processor_widget` method for
            more detailed documentation.

        :param parent_widget: The parent widget.

        :returns: A custom widget.
        """
        return None

    def get_nuke_shot_exporter_ui_properties(self):
        """
        Gets a list of property dictionaries describing the custom properties
        required by the custom widget. This method will only be run if the
        associated create widget hook method returns a widget. The dictionaries
        will be turned into property widgets by the app before being passed to
        the associated set properties hook method. The order that the dictionaries
        are returned by this method is maintained when they are passed to the
        associated set hook method.

        .. note:: See the :meth:`get_shot_processor_ui_properties` method for
            more detailed documentation.

        :returns: A list of dictionaries.
        :rtype: list
        """
        return []

    def set_nuke_shot_exporter_ui_properties(self, widget, properties):
        """
        Sets any custom properties described by get_nuke_shot_exporter_ui_properties
        on the custom widget returned by create_nuke_shot_exporter_widget. This method
        will only be called if the create method is implemented to return a custom
        widget. The order of the properties within the dictionary passed in is the
        same as the order they're returned in the get properties hook method.

        .. note:: See the :meth:`set_shot_processor_ui_properties` method for
            for an example implementation.

        :param widget: The Qt widget that was created by the associated create
            widget hook method.
        :param OrderedDict properties: A dict containing property widget
            objects, keyed by label, that were constructed from the data
            built by the associated get properties hook method.
        """
        return
