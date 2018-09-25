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


class CreateCutPlugin(HookBaseClass):
    """
    Plugin for creating generic publishes in Shotgun
    """

    def __init__(self, *args, **kwrds):
        super(CreateCutPlugin, self).__init__(*args, **kwrds)

        self.publisher = self.parent
        self.engine = self.publisher.engine
        self.sg = self.engine.shotgun

    @property
    def icon(self):
        """
        Path to an png icon on disk
        """
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
        return "Create new Cut Item"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """
        return "Creates cut items in Shotgun for the given object"

    @property
    def settings(self):
        """
        Dictionary defining the settings that this plugin expects to receive
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

        # Only available on Shot entity
        shot_context = item.context.entity and item.context.entity.get("type") == "Shot"

        # Not available from batch render
        accepted = cut_supported and shot_context and not item.properties.get("fromBatch", False)

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

        # Make sure that we have the context dict in the item properties
        if "context" not in item.properties:
            self.cache_entities(item.parent, [item.context.entity])
            item.properties["context"] = item.parent.properties["Shot"][item.context.entity["id"]]

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
                pass  # TODO

        return "Sequence" in item.properties["context"]

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

        # Check if a previous run had already created the Cut
        if "Cut" in item.properties["context"]["Sequence"]:
            cut = item.properties["context"]["Sequence"]["Cut"]

        # This is the first item creating the CutItem so we need to create the Cut
        else:
            # The cut name have the same code than the Sequence
            cut_code = item.properties["context"]["Sequence"]["code"]
            cut_fields = ["revision_number"]

            # Try to find the previous cut to determine the Cut revision number
            prev_cut = self.sg.find_one(
                "Cut",
                [["code", "is", cut_code],
                 ["entity", "is", item.properties["context"]["Sequence"]]],
                cut_fields,
                [{"field_name": "revision_number", "direction": "desc"}]
            )

            # Determine the revision number based on the previous Cut
            if prev_cut is None:
                next_revision_number = 1
            else:
                next_revision_number = prev_cut["revision_number"] + 1

            # Create the Cut
            cut = self.sg.create(
                "Cut",
                {
                    "project": item.context.project,
                    "entity": item.properties["context"]["Sequence"],
                    "code": cut_code,
                    "revision_number": next_revision_number,
                    "fps": float(asset_info["sequenceFps"])
                }
            )

            # Cache this cut!
            self.cache_entities(item.parent, [cut])

            # Save this Cut on the context to share it to the other items of the Sequence context
            item.properties["context"]["Sequence"]["Cut"] = item.parent.properties[cut["type"]][cut["id"]]

        # Build the CutItem information dictionary
        cut_item_data = self._cutitem_data(item)
        cut_item_data["cut"] = cut
        cut_item_data["shot"] = item.context.entity

        # Build the thumbnail generation target list
        targets = []

        # If this CutItem is the first element of the cut, update the thumbnail of the Cut
        if asset_info["segmentIndex"] == 1:
            targets.append(cut)

        # Create the CutItem
        cut_item = self.sg.create("CutItem", cut_item_data)

        # Cache that CutItem
        self.cache_entities(item.parent, [cut_item])

        # Save that CutItem in the Context
        item.properties["context"]["CutItem"] = item.parent.properties[cut_item["type"]][cut_item["id"]]

        # Add the CutItem to the thumbnail generation target list
        targets.append(cut_item)

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
        # We only want to run that finalize step once
        if "Cut" in item.properties["context"]["Sequence"]:
            # Get all CutItem linked to this Cut
            cut_items = self.sg.find(
                "CutItem",
                [["cut", "is", item.properties["context"]["Sequence"]["Cut"]]],
                ["timecode_edit_in_text", "timecode_edit_out_text", "cut_item_duration"],
                [{"field_name": "cut_order", "direction": "asc"}]  # We want them sorted to save time later
            )

            # Build the Cut metadata
            cut_data = {
                "duration": sum([int(cut_item["cut_item_duration"]) for cut_item in cut_items]),  # Sum of the CutItems
                "timecode_start_text": cut_items[0]["timecode_edit_in_text"],  # Beginning of the first CutItem
                "timecode_end_text": cut_items[-1]["timecode_edit_out_text"]  # End of the last CutItem
            }

            # Update teh Cut metadata
            self.sg.update("Cut", item.properties["context"]["Sequence"]["Cut"]["id"], cut_data)

            # Delete the Cut in the context to ensure that the finalization step is not repeated
            del item.properties["context"]["Sequence"]["Cut"]

        self.engine.thumbnail_generator.finalize(path=item.properties["path"])

    def _cutitem_data(self, item):
        """
        Extract the CutItem metadata from the item assetInfo

        :param item: Current Item
        :return: CutItem metadata dictionary
        """
        asset_info = item.properties["assetInfo"]

        cutitem_data = {
            "cut_item_in": asset_info["sourceIn"] + asset_info["handleIn"],
            "cut_item_out": asset_info["sourceOut"] - asset_info["handleOut"] - 1,
            "edit_in": asset_info["recordIn"],
            "edit_out": asset_info["recordOut"] - 1,
            "project": item.context.project,
            "description": item.description,
            "shot": item.properties.get("Shot"),
            "code": asset_info["assetName"],
            "version": item.properties.get("Version"),
            "cut_order": asset_info["segmentIndex"]
        }

        cutitem_data["cut_item_duration"] = cutitem_data["cut_item_out"] - cutitem_data["cut_item_in"] + 1

        # Generate the timecode based fields
        cutitem_data["timecode_cut_item_in_text"] = self._frames_to_timecode(cutitem_data["cut_item_in"],
                                                                             drop=asset_info["drop"],
                                                                             frame_rate=float(asset_info["fps"]))

        cutitem_data["timecode_cut_item_out_text"] = self._frames_to_timecode(cutitem_data["cut_item_out"],
                                                                              drop=asset_info["drop"],
                                                                              frame_rate=float(asset_info["fps"]))

        cutitem_data["timecode_edit_in_text"] = self._frames_to_timecode(cutitem_data["edit_in"],
                                                                         drop=asset_info["sequenceDrop"],
                                                                         frame_rate=float(asset_info["sequenceFps"]))

        cutitem_data["timecode_edit_out_text"] = self._frames_to_timecode(cutitem_data["edit_out"],
                                                                          drop=asset_info["sequenceDrop"],
                                                                          frame_rate=float(asset_info["sequenceFps"]))

        return cutitem_data

    def _frames_to_timecode(self, total_frames, frame_rate, drop):
        """
        Helper method that converts frames to SMPTE timecode.

        :param total_frames: Number of frames
        :param frame_rate: frames per second
        :param drop: true if time code should drop frames, false if not
        :returns: SMPTE timecode as string, e.g. '01:02:12:32' or '01:02:12;32'
        """
        if drop and frame_rate not in [29.97, 59.94]:
            raise NotImplementedError("Time code calculation logic only supports drop frame "
                                      "calculations for 29.97 and 59.94 fps.")

        # for a good discussion around time codes and sample code, see
        # http://andrewduncan.net/timecodes/

        # round fps to the nearest integer
        # note that for frame rates such as 29.97 or 59.94,
        # we treat them as 30 and 60 when converting to time code
        # then, in some cases we 'compensate' by adding 'drop frames',
        # e.g. jump in the time code at certain points to make sure that
        # the time code calculations are roughly right.
        #
        # for a good explanation, see
        # https://documentation.apple.com/en/finalcutpro/usermanual/index.html#chapter=D%26section=6
        fps_int = int(round(frame_rate))

        if drop:
            # drop-frame-mode
            # add two 'fake' frames every minute but not every 10 minutes
            #
            # example at the one minute mark:
            #
            # frame: 1795 non-drop: 00:00:59:25 drop: 00:00:59;25
            # frame: 1796 non-drop: 00:00:59:26 drop: 00:00:59;26
            # frame: 1797 non-drop: 00:00:59:27 drop: 00:00:59;27
            # frame: 1798 non-drop: 00:00:59:28 drop: 00:00:59;28
            # frame: 1799 non-drop: 00:00:59:29 drop: 00:00:59;29
            # frame: 1800 non-drop: 00:01:00:00 drop: 00:01:00;02
            # frame: 1801 non-drop: 00:01:00:01 drop: 00:01:00;03
            # frame: 1802 non-drop: 00:01:00:02 drop: 00:01:00;04
            # frame: 1803 non-drop: 00:01:00:03 drop: 00:01:00;05
            # frame: 1804 non-drop: 00:01:00:04 drop: 00:01:00;06
            # frame: 1805 non-drop: 00:01:00:05 drop: 00:01:00;07
            #
            # example at the ten minute mark:
            #
            # frame: 17977 non-drop: 00:09:59:07 drop: 00:09:59;25
            # frame: 17978 non-drop: 00:09:59:08 drop: 00:09:59;26
            # frame: 17979 non-drop: 00:09:59:09 drop: 00:09:59;27
            # frame: 17980 non-drop: 00:09:59:10 drop: 00:09:59;28
            # frame: 17981 non-drop: 00:09:59:11 drop: 00:09:59;29
            # frame: 17982 non-drop: 00:09:59:12 drop: 00:10:00;00
            # frame: 17983 non-drop: 00:09:59:13 drop: 00:10:00;01
            # frame: 17984 non-drop: 00:09:59:14 drop: 00:10:00;02
            # frame: 17985 non-drop: 00:09:59:15 drop: 00:10:00;03
            # frame: 17986 non-drop: 00:09:59:16 drop: 00:10:00;04
            # frame: 17987 non-drop: 00:09:59:17 drop: 00:10:00;05

            # calculate number of drop frames for a 29.97 std NTSC
            # workflow. Here there are 30*60 = 1800 frames in one
            # minute

            FRAMES_IN_ONE_MINUTE = 1800 - 2

            FRAMES_IN_TEN_MINUTES = (FRAMES_IN_ONE_MINUTE * 10) - 2

            ten_minute_chunks = total_frames / FRAMES_IN_TEN_MINUTES
            one_minute_chunks = total_frames % FRAMES_IN_TEN_MINUTES

            ten_minute_part = 18 * ten_minute_chunks
            one_minute_part = 2 * ((one_minute_chunks - 2) / FRAMES_IN_ONE_MINUTE)

            if one_minute_part < 0:
                one_minute_part = 0

            # add extra frames
            total_frames += ten_minute_part + one_minute_part

            # for 60 fps drop frame calculations, we add twice the number of frames
            if fps_int == 60:
                total_frames = total_frames * 2

            # time codes are on the form 12:12:12;12
            smpte_token = ";"

        else:
            # time codes are on the form 12:12:12:12
            smpte_token = ":"

        # now split our frames into time code
        hours = int(total_frames / (3600 * fps_int))
        minutes = int(total_frames / (60 * fps_int) % 60)
        seconds = int(total_frames / fps_int % 60)
        frames = int(total_frames % fps_int)
        return "%02d:%02d:%02d%s%02d" % (hours, minutes, seconds, smpte_token, frames)

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
