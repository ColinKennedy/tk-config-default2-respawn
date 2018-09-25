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


class UpdateShotPlugin(HookBaseClass):
    """
    Plugin for pushing Shot metadata in Shotgun
    """

    def __init__(self, *args, **kwrds):
        super(UpdateShotPlugin, self).__init__(*args, **kwrds)

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
        return "Update Shot"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return "Update shot in Shotgun for the given object"

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

        # Only available on a Shot Context and from a batch render
        is_accepted = item.context.entity and item.context.entity.get("type") == "Shot" and not item.properties.get("fromBatch", False)

        return {"accepted": is_accepted}

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
        # Make sure that we have the context dict in the item properties
        if "context" not in item.properties:
            self.cache_entities(item.parent, [item.context.entity])
            item.properties["context"] = item.parent.properties[item.context.entity["type"]][item.context.entity["id"]]

        # Make sure that we have the Sequence in our context dict
        if "Sequence" not in item.properties["context"]:
            sequence_fields = ["cuts", "shots", "code"]
            sequence = self.sg.find_one("Sequence", [["shots", "is", item.context.entity]], sequence_fields)
            self.cache_entities(item.parent, [sequence])

            if sequence \
                    and sequence["type"] in item.parent.properties and \
                            sequence["id"] in item.parent.properties[sequence["type"]]:
                item.properties["context"]["Sequence"] = item.parent.properties[sequence["type"]][sequence["id"]]
            else:
                pass

        return "Sequence" in item.properties["context"]

    def publish(self, settings, item):
        """
        Executes the publish logic for the given item and settings.

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        """
        shot_data = self._shot_data(item)
        asset_info = item.properties["assetInfo"]
        path = item.properties["path"]

        # Build the thumbnail generation target list
        target = [item.context.entity]

        # If this is the first Shot of the Sequence, we update the Sequence thumbnail
        if asset_info["segmentIndex"] == 1:
            sequence = item.properties["context"]["Sequence"]
            target.append(sequence)

        # Update the Shot on shotgun
        self.sg.update("Shot", item.context.entity['id'], shot_data)

        # Create the Image thumbnail in background
        self.engine.thumbnail_generator.generate(
            display_name=item.name,
            path=path,
            dependencies=item.properties.get("backgroundJobId"),
            target_entities=target,
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

    def _shot_data(self, item):
        """
        Extract the Shot metadata from the item assetInfo

        :param item: Current Item
        :return: Shot metadata dictionary
        """
        asset_info = item.properties["assetInfo"]

        shot_data = {
            "description": item.description,
            "sg_cut_in": asset_info["recordIn"],
            "sg_cut_out": asset_info["recordOut"] - 1,
            "sg_cut_order": asset_info["segmentIndex"],
        }

        shot_data["sg_head_in"] = shot_data["sg_cut_in"] - asset_info["handleIn"]
        shot_data["sg_tail_out"] = shot_data["sg_cut_out"] + asset_info["handleOut"]

        shot_data["sg_cut_duration"] = shot_data["sg_cut_out"] - shot_data["sg_cut_in"] + 1
        shot_data["sg_working_duration"] = shot_data["sg_tail_out"] - shot_data["sg_head_in"] + 1

        return shot_data

    def cache_entities(self, parent_item, entities):
        """
        Cache the entity list on the item properties to avoid redundant database query.

        :param item: Item instance where the entities should be cached on
        :param entities: List of entity to cache
        """
        for entity in entities:
            entity_type = entity["type"]
            entity_id = entity["id"]
            if entity_type not in parent_item.properties:
                parent_item.properties[entity_type] = {entity_id: dict(entity)}
            elif entity_id not in parent_item.properties[entity_type]:
                parent_item.properties[entity_type][entity_id] = dict(entity)
            else:
                parent_item.properties[entity_type][entity_id].update(entity)
