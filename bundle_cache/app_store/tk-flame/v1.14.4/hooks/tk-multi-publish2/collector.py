# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Ccollect_current_sceneode License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import mimetypes
import os
import re

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

# This is a dictionary of file type info that allows the basic collector to
# identify common production file types and associate them with a display name,
# item type, and config icon.
COMMON_FILE_INFO = {
    "Alembic Cache": {
        "extensions": ["abc"],
        "icon": "alembic.png",
        "item_type": "file.alembic",
    },
    "3dsmax Scene": {
        "extensions": ["max"],
        "icon": "3dsmax.png",
        "item_type": "file.3dsmax",
    },
    "Hiero Project": {
        "extensions": ["hrox"],
        "icon": "hiero.png",
        "item_type": "file.hiero",
    },
    "Houdini Scene": {
        "extensions": ["hip", "hipnc"],
        "icon": "houdini.png",
        "item_type": "file.houdini",
    },
    "Maya Scene": {
        "extensions": ["ma", "mb"],
        "icon": "maya.png",
        "item_type": "file.maya",
    },
    "Nuke Script": {
        "extensions": ["nk"],
        "icon": "nuke.png",
        "item_type": "file.nuke",
    },
    "Photoshop Image": {
        "extensions": ["psd", "psb"],
        "icon": "photoshop.png",
        "item_type": "file.photoshop",
    },
    "Rendered Image": {
        "extensions": ["dpx", "exr"],
        "icon": "image_sequence.png",
        "item_type": "file.image",
    },
    "Texture Image": {
        "extensions": ["tiff", "tx", "tga", "dds", "rat"],
        "icon": "texture.png",
        "item_type": "file.texture",
    },
    "Open Clip": {
        "extensions": ["clip"],
        "icon": "flame.png",
        "item_type": "file.openClip",
    },
    "Flame Batch File": {
        "extensions": ["batch"],
        "icon": "SG_Batch.png",
        "item_type": "file.batch",
    }
}


class FlameItemCollector(HookBaseClass):
    """
    A basic collector that handles files and general objects.
    """

    def __init__(self, *args, **kwrds):
        super(FlameItemCollector, self).__init__(*args, **kwrds)

        self.publisher = self.parent
        self.engine = self.publisher.engine
        self.sg = self.engine.shotgun

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """
        return {
            "Task Templates": {
                "type": "dict",
                "default": {
                    "Shot": "Basic shot template"
                },
                "description": "Task template to use on entity creation (Entity -> Task Template)"
            }
        }

    def process_current_session(self, settings, parent_item):
        """
        Create Items from the flame latest export action.

        This action could be an Export from the MediaLibrary or a Render from Batch.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        """

        try:
            self.engine.show_busy("Preparing Publish...", "Collecting assets to publish...")

            task_templates_setting = settings.get("Task Templates", None)
            task_templates_names = task_templates_setting.value if task_templates_setting else {}

            shot_task_template_code, shot_task_template = task_templates_names.get("Shot", ""), None
            if shot_task_template_code:
                shot_task_template = self.sg.find_one(
                    "TaskTemplate",
                    [["code", "is", shot_task_template_code]]
                )

            sequence_task_template_code, sequence_task_template = task_templates_names.get("Sequence", ""), None
            if sequence_task_template_code:
                sequence_task_template = self.sg.find_one(
                    "TaskTemplate",
                    [["code", "is", sequence_task_template_code]]
                )

            # Current project
            project = self.publisher.context.project

            # Flame export last export info
            export_context = self.engine.export_info

            # Shotgun queries constants
            shot_fields = ["code", "sg_cut_in", "sg_cut_out", "sg_head_in", "sg_tail_out"]
            sequence_fields = ["cuts", "shots", "code"]
            sort_by_fields = [{"field_name": "created_at", "direction": "desc"}]

            # When the action is an Export, the export_info is an embedded dictionary structure
            if isinstance(export_context, dict):

                # The first level of dictionary have the Sequence name as key and another dictionary as value
                for sequence_name, sequence_info in sorted(export_context.items()):
                    sequence = None

                    # If the sequence_name is not ""
                    if sequence_name:

                        # We try to find a Sequence with the right code. The latest if there's more thant one Sequence.
                        sg_filter = [["code", "is", sequence_name], ["project", "is", project]]
                        sequence = self.sg.find_one("Sequence", sg_filter, sequence_fields, sort_by_fields)

                        if not sequence:
                            # There's no Sequence with the right code... Let's create one!
                            seq_data = {
                                "code": sequence_name,
                                "project": project,
                                "task_template": sequence_task_template
                            }

                            sequence = self.sg.create("Sequence", seq_data)

                        # Let's cache this Sequence information
                        self.cache_entities(parent_item, [sequence])

                    # The second level of dictionary have the Shot name as key and another dictionary as value
                    for shot_name, shot_info in sorted(sequence_info.items()):
                        shot = None

                        # If the shot_name is not ""
                        if shot_name:
                            # The Shot should have the right code name
                            sg_filter = [["code", "is", shot_name]]

                            if sequence:
                                # The shot should be linked to the right Sequence
                                sg_filter.append(["sg_sequence", "is", sequence])

                                # We try to find the right Shot. The latest if there's more thant one Shot.
                                shot = self.sg.find_one("Shot", sg_filter, shot_fields, sort_by_fields)

                            if not shot:
                                # There's no Shot that match our needs... so let's create it !
                                shot_data = {
                                    "code": shot_name,
                                    "project": project,
                                    "task_template": shot_task_template
                                }

                                if sequence:
                                    # It should be linked to the sequence that we fount previously
                                    shot_data["sg_sequence"] = sequence

                                shot = self.sg.create("Shot", shot_data)

                            # Let's cache this Shot information
                            self.cache_entities(parent_item, [shot])

                        # We use a shared job_id_list on a Shot level because there's no background job ID associated to a
                        # OpenClip file export. If we trigger a thumbnail generation when the real media is not available,
                        # it fail. Making a long dependency list ensure that every video/movie item is rendered before we try to
                        # generate the thumbnails.
                        job_id_list = []

                        # Whe want to have the items in a sorted way
                        key_order = ["batchOpenClip", "batch", "openClip", "video", "movie", "audio", "sequence"]

                        # The next level of dictionary have the asset type as key and a dictionary as value
                        for asset_type, asset_type_info in sorted(shot_info.items(), key=lambda i: key_order.index(i[0])):

                            # The next level of dictionary have the asset name as key and a list as value
                            for _, asset_info_list in asset_type_info.items():

                                # Finally, this is a list of asset with the same name, type, shot and sequence.
                                for asset_info in asset_info_list:

                                    # Dynamically get the right function based on the type
                                    if hasattr(self, "create_{}_items".format(asset_type)):
                                        create_items = getattr(self, "create_{}_items".format(asset_type))
                                    else:
                                        # This is a new assetType and not supported by the this collector
                                        continue

                                    # Get the items that can be created from this asset
                                    items = create_items(parent_item, asset_info)
                                    for item in items:
                                        # This is not an item from a batch render
                                        item.properties["fromBatch"] = False

                                        # Let's keep a reference to the asset info dict
                                        item.properties["assetInfo"] = asset_info

                                        # Let's keep a reference to the shared job id list
                                        item.properties["backgroundJobId"] = job_id_list

                                        # Add the current asset job id if there's one
                                        job_id = asset_info.get("backgroundJobId")
                                        if job_id:
                                            item.properties["backgroundJobId"].append(job_id)

                                        # Set the context based on the most precise entity available
                                        if shot:
                                            item.context = self.publisher.sgtk.context_from_entity_dictionary(shot)
                                        elif sequence:
                                            item.context = self.publisher.sgtk.context_from_entity_dictionary(sequence)
                                        else:
                                            item.context = self.publisher.sgtk.context_from_entity_dictionary(project)

                                        # This item cannot have another context than this one
                                        item.context_change_allowed = False

            # When the action is a render, the export_info is a list of asset
            elif isinstance(export_context, list):
                # We have a list of asset
                for asset_info in export_context:
                    shot = None
                    shot_name = asset_info.get("shotName", "")

                    # We try to find the right Shot. The latest if there's more thant one Shot.
                    if shot_name:
                        sg_filter = [["code", "is", shot_name]]
                        shot = self.sg.find_one("Shot", sg_filter, shot_fields, sort_by_fields)

                    # The fallback is to try to find the PublishedFile linked to the shot OpenClip and use the same entity
                    if not shot and "openClipResolvedPath" in asset_info:
                        filters = [["project", "is", project]]
                        fields = ["path", "entity"]

                        # Get all PublishedFile of the current project
                        published_files = self.parent.shotgun.find(
                            "PublishedFile", filters=filters, fields=fields
                        )

                        # Try to find a PublishedFile with the same path as the OpenClip
                        for publish_file in published_files:
                            if asset_info["openClipResolvedPath"] in publish_file.get("path", {}).get("url", ""):
                                shot = publish_file.get("entity", None)
                                break

                    # Get the items that can be created from this asset dictionary
                    items = self.create_render_items(parent_item, asset_info)
                    for item in items:
                        # This item is from a batch render
                        item.properties["fromBatch"] = True

                        # Let's keep a reference to the asset info dict
                        item.properties["assetInfo"] = asset_info

                        # TODO: Rendering with Background Reactor trigger the postRender hook and start the publish
                        # process. This implies that the media might not be ready at the thumbnail generation and return
                        # an error. Right now, the background job fail and retry later until the moment when the media is
                        # ready, but we might want to have a cleaner way to handle this case.

                        # Set the context based on the most precise entity available
                        if shot:
                            self.cache_entities(parent_item, [shot])
                            item.context = self.publisher.sgtk.context_from_entity_dictionary(shot)
                        else:
                            item.context = self.publisher.sgtk.context_from_entity_dictionary(project)

                        # This item cannot have another context than this one
                        item.context_change_allowed = False
        finally:
            self.engine.clear_busy()

    def cache_entities(self, item, entities):
        """
        Cache the entity list on the item properties to avoid redundant database query.

        :param item: Item instance where the entities should be cached on
        :param entities: List of entity to cache
        """
        for entity in entities:
            entity_type = entity["type"]
            entity_id = entity["id"]

            if entity_type not in item.properties:
                item.properties[entity_type] = {entity_id: dict(entity)}
            elif entity_id not in item.properties[entity_type]:
                item.properties[entity_type][entity_id] = dict(entity)
            else:
                item.properties[entity_type][entity_id].update(entity)

    def create_render_items(self, parent_item, asset_info):
        """
        Create the items associated to a render information dictionary.

        :param parent_item: Parent of the items to create
        :param asset_info: Information dictionary related to a render action
        :return: List of Item
        """
        source_info = re.match(r".*\[(\d+)-(\d+)\].+", asset_info["resolvedPath"])
        if source_info:
            asset_info["sourceIn"] = int(source_info.group(1))
            asset_info["sourceOut"] = int(source_info.group(2)) + 1

        video_info = asset_info.copy()
        video_info["path"] = video_info["resolvedPath"]
        video = self.create_video_items(parent_item, asset_info)

        re.match(r"(.*)(\[\d+-\d+\])(.+)", asset_info["resolvedPath"])

        batch, openclip = [None], [None]
        if "setupResolvedPath" in asset_info:
            batch_info = asset_info.copy()
            batch_info["path"] = batch_info["setupResolvedPath"]
            batch = self.create_batch_items(parent_item, batch_info)

        if "openClipResolvedPath" in asset_info:
            openclip_info = asset_info.copy()
            openclip_info["path"] = openclip_info["openClipResolvedPath"]
            openclip = self.create_batchOpenClip_items(parent_item, openclip_info)

        return [item for item in video + batch + openclip if item is not None]

    def create_batch_items(self, parent_item, asset_info):
        """
        Create items based on a batch asset dictionary.

        :param parent_item: Parent of the items to create
        :param asset_info: Information dictionary related to a batch asset
        :return: List of Item
        """
        path = self._path_from_asset(asset_info)
        icon = os.path.join(self.disk_location, "icons", "SG_Batch.png")

        name = self.parent.util.get_publish_name(path)

        item = parent_item.create_item(
            "flame.batch",
            "Flame Batch File",
            name
        )
        item.set_icon_from_path(icon)
        item.thumbnail_enabled = False

        item.properties["path"] = path

        return [item]

    def create_batchOpenClip_items(self, parent_item, asset_info):
        """
        Create items based on a batchOpenClip asset dictionary.

        :param parent_item: Parent of the items to create
        :param asset_info: Information dictionary related to a batchOpenClip asset
        :return: List of Item
        """
        path = self._path_from_asset(asset_info)
        icon = os.path.join(self.disk_location, "icons", "flame.png")

        name = self.parent.util.get_publish_name(path)

        item = parent_item.create_item(
            "flame.batchOpenClip",
            "Flame Batch OpenClip",
            name
        )
        item.set_icon_from_path(icon)
        item.thumbnail_enabled = False

        item.properties["path"] = path

        return [item]

    def create_openClip_items(self, parent_item, asset_info):
        """
        Create items based on an openClip asset dictionary.

        :param parent_item: Parent of the items to create
        :param asset_info: Information dictionary related to an openClip asset
        :return: List of Item
        """
        path = self._path_from_asset(asset_info)
        icon = os.path.join(self.disk_location, "icons", "flame.png")

        name = self.parent.util.get_publish_name(path)

        item = parent_item.create_item(
            "flame.openClip",
            "Flame OpenClip",
            name
        )
        item.set_icon_from_path(icon)
        item.thumbnail_enabled = False

        item.properties["path"] = path

        return [item]

    def create_video_items(self, parent_item, asset_info):
        """
        Create items based on a video asset dictionary.

        :param parent_item: Parent of the items to create
        :param asset_info: Information dictionary related to a video asset
        :return: List of Item
        """
        path = self._path_from_asset(asset_info)
        sequence = self._get_file_sequence(path)
        icon = os.path.join(self.disk_location, "icons", "image_sequence.png")

        # get the publish name for this file path.
        is_sequence = len(sequence) != 0

        if is_sequence:
            # generate the name from one of the actual files in the sequence
            name_path = self.publisher.util.get_frame_sequence_path(sequence[0])
        else:
            name_path = path

        # get the publish name for this file path. this will ensure we get a
        # consistent name across version publishes of this file.
        name = self.parent.util.get_publish_name(
            name_path, sequence=is_sequence)

        item = parent_item.create_item(
            "flame.video",
            "Flame Render",
            name
        )
        item.set_icon_from_path(icon)
        item.thumbnail_enabled = False

        if sequence:
            item.properties["is_sequence"] = True
            item.properties["sequence_files"] = sequence

        item.properties["path"] = name_path
        item.properties["file_path"] = path

        return [item]

    def create_movie_items(self, parent_item, asset_info):
        """
        Create items based on a movie asset dictionary.

        :param parent_item: Parent of the items to create
        :param asset_info: Information dictionary related to a movie asset
        :return: List of Item
        """
        path = self._path_from_asset(asset_info)
        icon = os.path.join(self.disk_location, "icons", "video.png")

        # get the publish name for this file path. this will ensure we get a
        # consistent name across version publishes of this file.
        name = self.parent.util.get_publish_name(path)

        item = parent_item.create_item(
            "flame.movie",
            "Flame Render",
            name
        )
        item.set_icon_from_path(icon)
        item.thumbnail_enabled = False

        item.properties["path"] = path

        return [item]

    def create_audio_items(self, parent_item, asset_info):
        """
        Create items based on an audio asset dictionary.

        :param parent_item: Parent of the items to create
        :param asset_info: Information dictionary related to an audio asset
        :return: List of Item
        """
        path = self._path_from_asset(asset_info)
        icon = os.path.join(self.disk_location, "icons", "audio.png")

        name = self.parent.util.get_publish_name(path)

        item = parent_item.create_item(
            "flame.audio",
            "Flame Audio",
            name
        )
        item.set_icon_from_path(icon)
        item.thumbnail_enabled = False

        item.properties["path"] = path

        return [item]

    def create_sequence_items(self, parent_item, asset_info):
        """
        Create items based on a sequence asset dictionary.

        :param parent_item: Parent of the items to create
        :param asset_info: Information dictionary related to a sequence asset
        :return: List of Item
        """
        path = self._path_from_asset(asset_info)
        icon = os.path.join(self.disk_location, "icons", "flame.png")

        name = self.parent.util.get_publish_name(path)

        item = parent_item.create_item(
            "flame.sequence",
            "Flame Sequence",
            name
        )
        item.set_icon_from_path(icon)
        item.thumbnail_enabled = False

        item.properties["path"] = path

        return [item]

    @staticmethod
    def _path_from_asset(asset_info):
        """
        Extract the path from the given asset information dictionary

        :param asset_info: Asset information dictionary
        :return: Path of the asset
        """
        # If the path key is present on the asset_info dictionary, let's use it
        if "path" in asset_info:
            path = asset_info["path"]
        else:
            # Avoiding the os.path.join because resolvedPath might start with /
            path = os.path.normpath(
                os.path.sep.join([asset_info.get("destinationPath", ""),
                                  asset_info["resolvedPath"]]))

        return path

    def process_file(self, parent_item, path):
        """
        Analyzes the given file and creates one or more items
        to represent it.

        :param parent_item: Root item instance
        :param path: Path to analyze
        :returns: The main item that was created, or None if no item was created
            for the supplied path
        """

        # handle files and folders differently
        if os.path.isdir(path):
            self._collect_folder(parent_item, path)
            return None
        else:
            return self._collect_file(parent_item, path)

    def _collect_file(self, parent_item, path, frame_sequence=False):
        """
        Process the supplied file path.

        :param parent_item: parent item instance
        :param path: Path to analyze
        :param frame_sequence: Treat the path as a part of a sequence
        :returns: The item that was created
        """

        # make sure the path is normalized. no trailing separator, separators
        # are appropriate for the current os, no double separators, etc.
        path = sgtk.util.ShotgunPath.normalize(path)

        publisher = self.parent

        # get info for the extension
        item_info = self._get_item_info(path)
        item_type = item_info["item_type"]
        type_display = item_info["type_display"]
        evaluated_path = path
        is_sequence = False

        if frame_sequence:
            # replace the frame number with frame spec
            seq_path = publisher.util.get_frame_sequence_path(path)
            if seq_path:
                evaluated_path = seq_path
                type_display = "%s Sequence" % (type_display,)
                item_type = "%s.%s" % (item_type, "sequence")
                is_sequence = True

        display_name = publisher.util.get_publish_name(
            path, sequence=is_sequence)

        # create and populate the item
        file_item = parent_item.create_item(
            item_type, type_display, display_name)

        # if the supplied path is an image, use the path as # the thumbnail.
        if (item_type.startswith("file.image") or
                item_type.startswith("file.texture")):
            file_item.set_thumbnail_from_path(path)

            # disable thumbnail creation since we get it for free
            file_item.thumbnail_enabled = False

        # all we know about the file is its path. set the path in its
        # properties for the plugins to use for processing.
        file_item.properties["path"] = evaluated_path

        icon = os.path.join(self.disk_location, "icons", item_info["icon_name"])
        file_item.set_icon_from_path(icon)

        if is_sequence:
            # include an indicator that this is an image sequence and the known
            # file that belongs to this sequence
            file_item.properties["is_sequence"] = True
            file_item.properties["sequence_files"] = [path]

        self.logger.info("Collected file: %s" % (evaluated_path,))

        return file_item

    def _collect_folder(self, parent_item, folder):
        """
        Process the supplied folder path.

        :param parent_item: parent item instance
        :param folder: Path to analyze
        :returns: The item that was created
        """

        # make sure the path is normalized. no trailing separator, separators
        # are appropriate for the current os, no double separators, etc.
        folder = sgtk.util.ShotgunPath.normalize(folder)

        publisher = self.parent
        img_sequences = publisher.util.get_frame_sequences(
            folder)

        file_items = []

        for (image_seq_path, img_seq_files) in img_sequences:
            # get info for the extension
            item_info = self._get_item_info(image_seq_path)
            item_type = item_info["item_type"]
            type_display = item_info["type_display"]

            # the supplied image path is part of a sequence. alter the
            # type info to account for this.
            type_display = "%s Sequence" % (type_display,)
            item_type = "%s.%s" % (item_type, "sequence")
            icon_name = "image_sequence.png"
            icon_path = os.path.join(self.disk_location, "icons", icon_name)

            # get the first frame of the sequence. we'll use this for the
            # thumbnail and to generate the display name
            img_seq_files.sort()
            first_frame_file = img_seq_files[0]
            display_name = publisher.util.get_publish_name(
                first_frame_file, sequence=True)

            # create and populate the item
            file_item = parent_item.create_item(
                item_type,
                type_display,
                display_name
            )

            file_item.set_icon_from_path(icon_path)

            # use the first frame of the seq as the thumbnail
            file_item.set_thumbnail_from_path(first_frame_file)

            # disable thumbnail creation since we get it for free
            file_item.thumbnail_enabled = False

            # all we know about the file is its path. set the path in its
            # properties for the plugins to use for processing.
            file_item.properties["path"] = image_seq_path
            file_item.properties["is_sequence"] = True
            file_item.properties["sequence_files"] = img_seq_files

            self.logger.info("Collected file: %s" % (image_seq_path,))

            file_items.append(file_item)

        if not file_items:
            self.logger.warn("No image sequences found in: %s" % (folder,))

        return file_items

    def _get_item_info(self, path):
        """
        Return a tuple of display name, item type, and icon path for the given
        filename.

        The method will try to identify the file as a common file type. If not,
        it will use the mimetype category. If the file still cannot be
        identified, it will fallback to a generic file type.

        :param path: The file path to identify type info for

        :return: A dictionary of information about the item to create::

            # path = "/path/to/some/file.0001.exr"

            {
                "item_type": "file.image.sequence",
                "type_display": "Rendered Image Sequence",
                "icon_path": "/path/to/some/icons/folder/image_sequence.png",
                "path": "/path/to/some/file.%04d.exr"
            }

        The item type will be of the form `file.<type>` where type is a specific
        common type or a generic classification of the file.
        """

        publisher = self.parent

        # extract the components of the supplied path
        file_info = publisher.util.get_file_path_components(path)
        extension = file_info["extension"]
        filename = file_info["filename"]

        # default values used if no specific type can be determined
        type_display = "File"
        item_type = "file.unknown"
        icon_name = "file.png"

        # keep track if a common type was identified for the extension
        common_type_found = False

        # look for the extension in the common file type info dict
        for display in COMMON_FILE_INFO:
            type_info = COMMON_FILE_INFO[display]

            if extension in type_info["extensions"]:
                # found the extension in the common types lookup. extract the
                # item type, icon name.
                type_display = display
                item_type = type_info["item_type"]
                icon_name = type_info["icon"]
                common_type_found = True
                break

        if not common_type_found:
            # no common type match. try to use the mimetype category. this will
            # be a value like "image/jpeg" or "video/mp4". we'll extract the
            # portion before the "/" and use that for display.
            (category_type, _) = mimetypes.guess_type(filename)

            if category_type:
                # the category portion of the mimetype
                category = category_type.split("/")[0]

                type_display = "%s File" % (category.title(),)
                item_type = "file.%s" % (category,)
                icon_name = "%s.png" % (category,)

        # everything should be populated. return the dictionary
        return dict(
            item_type=item_type,
            type_display=type_display,
            icon_name=icon_name,
            path=path
        )

    @staticmethod
    def _get_file_sequence(path):
        """
        Return a list of path from a file sequence path.

        "/a/b.[01-02].jpg" -> ["/a/b.01.jpg", "/a/b.02.jpg"]

        :param path: Path of the file sequence
        :return: List of path
        """
        match = re.match(r"(.*\.)((?:\[\d+-\d+\])|(?:\d+))(\..*)", path)
        if not match:
            return [] # The path is not a sequence

        # Get the first and last frame of the sequence
        frame_range = match.group(2).replace("[", "").replace("]", "").split("-")
        if len(frame_range) == 1:
            last = first = frame_range[0]
        else:
            first, last = frame_range

        # Get the frame value padding length
        frame_size = len(first)

        file_sequence = []
        for frame in range(int(first), int(last)):
            # Apply frame padding
            frame = "0" * (frame_size - len(str(frame))) + str(frame)

            # Build frame file name
            file_name = match.group(1) + frame + match.group(3)
            file_sequence.append(file_name)

        return file_sequence
