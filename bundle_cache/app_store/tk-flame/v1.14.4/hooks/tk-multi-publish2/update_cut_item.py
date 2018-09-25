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

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class UpdateCutPlugin(HookBaseClass):
    """
    Plugin for creating generic publishes in Shotgun
    """

    def __init__(self, *args, **kwrds):
        super(UpdateCutPlugin, self).__init__(*args, **kwrds)

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
        return "Update Cut Item"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return "Update cut items in Shotgun for the given object"

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
        return ["flame.batchOpenClip"]

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
        # Make sure that the Shotgun backend support Cuts
        cut_supported = self.sg.server_caps.version >= (7, 0, 0)

        # Only available on Shot context
        shot_context = item.context.entity and item.context.entity.get("type") == "Shot"

        accepted = cut_supported and shot_context and item.properties.get("fromBatch", False)

        # If the context is correct, try to find the CutItem to Update
        if accepted:
            item.properties["CutItem"] = self.sg.find_one("CutItem", [["shot", "is", item.context.entity]],
                                                          ["cut_order", "cut"], [
                                                              {"field_name": "cut.Cut.revision_number",
                                                               "direction": "desc"}])

            # Accept only if we know what CutItem to update
            accepted = item.properties["CutItem"] is not None

        return {"accepted": accepted}

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
        asset_info = item.properties["assetInfo"]
        path = item.properties["path"]

        cut_item = item.properties["CutItem"]
        version = item.properties.get("Version")

        # If the current Publish session had created a Version, we push it to the CutItem to update
        if version:
            self.sg.update("CutItem", cut_item["id"], {"version": version})

        # Build the thumbnail generation target list
        targets = [cut_item]

        # If the CutItem is the first one of the Cut, we update the Cut preview
        if cut_item["cut_order"] == 1:
            cut = cut_item["cut"]
            targets.append(cut)

        # For file sequences, the hooks we want the path as provided by flame.
        path = item.properties.get("file_path", path)

        # Create the Image thumbnail in background
        self.engine.thumbnail_generator.generate(
            display_name=item.name,
            path=path,
            dependencies=item.properties.get("backgroundJobId"),
            target_entities=targets,
            asset_info=asset_info
        )

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

        self.engine.thumbnail_generator.finalize(path=item.properties["path"])
