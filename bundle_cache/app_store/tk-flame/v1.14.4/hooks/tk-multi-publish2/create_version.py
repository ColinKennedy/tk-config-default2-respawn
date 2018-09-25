# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import re

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class CreateVersionPlugin(HookBaseClass):
    """
    Plugin for creating generic publishes in Shotgun
    """

    def __init__(self, *args, **kwrds):
        super(CreateVersionPlugin, self).__init__(*args, **kwrds)

        self.publisher = self.parent
        self.engine = self.publisher.engine
        self.sg = self.engine.shotgun

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """

        # look for icon one level up from this hook's folder in "icons" folder
        return os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "publish.png"
        )

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Create Version"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return "Creates version in Shotgun for the given object"

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to recieve
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form:

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts
        as part of its environment configuration.
        """
        return {}

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """
        return ["flame.video", "flame.movie", "flame.openClip", "flame.batchOpenClip"]

    def accept(self, settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        return {"accepted": True}

    def validate(self, settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        return True

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        path = item.properties.get("path", None)

        # Build the Version metadata dictionary
        ver_data = dict(
            project=item.context.project,
            code=item.name,
            description=item.description,
            entity=item.context.entity,
            sg_task=item.context.task,
            sg_path_to_frames=path
        )

        ver_data["sg_department"] = "Flame"

        asset_info = item.properties.get("assetInfo", {})

        frame_rate = asset_info.get("fps")
        if frame_rate:
            ver_data["sg_uploaded_movie_frame_rate"] = float(frame_rate)

        aspect_ratio = asset_info.get("aspectRatio")
        if asset_info:
            ver_data["sg_frames_aspect_ratio"] = float(aspect_ratio)
            ver_data["sg_movie_aspect_ratio"] = float(aspect_ratio)

        # For file sequences, we want the path as provided by flame.
        # The property 'path' will be encoded the shotgun way file.%d.ext
        # while 'file_path' will be encoded the flame way file.[##-##].ext.
        file_path = item.properties.get("file_path", path)

        re_match = re.search("(\[[0-9]+-[0-9]+\])\.", file_path)
        if re_match:
            ver_data["frame_range"] = re_match.group(1)[1:-1]

        if "sourceIn" in asset_info and "sourceOut" in asset_info:
            ver_data["sg_first_frame"] = asset_info["sourceIn"]
            ver_data["sg_last_frame"] = asset_info["sourceOut"] - 1
            ver_data["frame_count"] = int(ver_data["sg_last_frame"]) - int(ver_data["sg_first_frame"]) + 1

        # Create the Version
        version = self.sg.create("Version", ver_data)

        # Keep the version reference for the other plugins
        item.properties["Version"] = version

        dependencies = item.properties.get("backgroundJobId")

        # Create the Movie preview in background
        # (Thumbnail will be generated server-side from movie)
        self.engine.thumbnail_generator.generate(
            display_name=item.name,
            path=file_path,
            dependencies=dependencies,
            target_entities=[version],
            asset_info=asset_info)

    def finalize(self, settings, item):
        """
        Execute the finalization pass. This pass executes once
        all the publish tasks have completed, and can for example
        be used to version up files.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """

        path = item.properties.get("path", None)
        file_path = item.properties.get("file_path", path)

        self.engine.thumbnail_generator.finalize(path=file_path)
