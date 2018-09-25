# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

__all__ = ["ThumbnailGenerator"]

class ThumbnailGenerator(object):
    """
    Abstract interface of a thumbnail generator of Flame's exported assets.
    """

    def __init__(self, engine):
        self._engine = engine

    @property
    def engine(self):
        """
        :returns the DCC engine:
        """
        return self._engine

    @staticmethod
    def _does_entity_support_preview(entity):
        """
        Returns True if the entity support movie preview
        :returns boolean:
        """
        return entity.get("type") == "Version"

    def generate(self, path, display_name, target_entities, asset_info, dependencies, favor_preview=True):
        """
        Generate a thumbnail or a preview for a given media asset and link
        it to a list of Shotgun entities. Multiple call to this method with
        same path but different target_entitie can be done to bundle jobs.

        :param path: Path to the media for which thumbnail or preview need to be
            generated and uploaded to Shotgun.
        :param display_name: The display name of the item we are generating the
            thumbnail for. This will usually be the based name of the path.
        :param target_entities: Target entities to which the thumbnails need to
            be linked to.
        :param asset_info: Dictionary of attribute passed by Flame's python
            hooks collected either thru an export (sg_export_hooks.py) or a
            batch render (sg_batch_hooks.py).
        :param dependencies: List of backburner job IDs this thumbnail
            generation job need to wait in order to be started. Can be None if
            the media is created in foreground.
        :param favor_preview: Movie previews will be favored over static
            thumbnails if the entity supports it.
        """

        # Split target entities in two groups, the ones that support movies
        # and the ones that dont since uploading a movie will generate also
        # a thumbnail
        bypass_server_transcoding = self.engine.get_setting("bypass_server_transcoding")
        if bypass_server_transcoding:
            self.engine.log_debug("Bypass Shotgun transcoding setting ENABLED.")

        generate_previews = favor_preview and self.engine.get_setting("generate_previews")
        if not generate_previews:
            self.engine.log_debug("Generation of preview DISABLED.")

        generate_thumbnails = self.engine.get_setting("generate_thumbnails")
        if not generate_thumbnails:
            self.engine.log_debug("Generation of thumbnail DISABLED.")

        preview_entities = []
        thumbnail_entities = []
        for target_entity in target_entities:
            if generate_previews and self._does_entity_support_preview(target_entity):
                preview_entities.append(target_entity)

                # Since the uploaded movie will not generate a thumbnail,
                # we need to upload a thumbnail too.
                if bypass_server_transcoding and generate_thumbnails:
                    thumbnail_entities.append(target_entity)
            elif generate_thumbnails:
                thumbnail_entities.append(target_entity)

        if len(preview_entities) > 0:
            self._generate_preview(
                path=path,
                display_name=display_name,
                target_entities=preview_entities,
                asset_info=asset_info,
                dependencies=dependencies
            )

        if len(thumbnail_entities) > 0:
            self._generate_thumbnail(
                path=path,
                display_name=display_name,
                target_entities=thumbnail_entities,
                asset_info=asset_info,
                dependencies=dependencies
            )

    def _generate_preview(self, path, display_name, target_entities, asset_info, dependencies):
        """
        Generate a preview for a given media asset and link
        it to a list of Shotgun entities. Multiple call to this method with
        same path but different target_entitie can be done to bundle jobs.

        :param path: Path to the media for which thumbnail or preview need to be
            generated and uploaded to Shotgun.
        :param display_name: The display name of the item we are generating the
            thumbnail for. This will usually be the based name of the path.
        :param target_entities: Target entities to which the thumbnails need to
            be linked to.
        :param asset_info: Dictionary of attribute passed by Flame's python
            hooks collected either thru an export (sg_export_hooks.py) or a
            batch render (sg_batch_hooks.py).
        :param dependencies: List of backburner job IDs this thumbnail
            generation job need to wait in order to be started. Can be None if
            the media is created in foreground.
        """
        raise NotImplementedError

    def _generate_thumbnail(self, path, display_name, target_entities, asset_info, dependencies):
        """
        Generate a thumbnail for a given media asset and link
        it to a list of Shotgun entities. Multiple call to this method with
        same path but different target_entitie can be done to bundle jobs.

        :param path: Path to the media for which thumbnail or preview need to be
            generated and uploaded to Shotgun.
        :param display_name: The display name of the item we are generating the
            thumbnail for. This will usually be the based name of the path.
        :param target_entities: Target entities to which the thumbnails need to
            be linked to.
        :param asset_info: Dictionary of attribute passed by Flame's python
            hooks collected either thru an export (sg_export_hooks.py) or a
            batch render (sg_batch_hooks.py).
        :param dependencies: List of backburner job IDs this thumbnail
            generation job need to wait in order to be started. Can be None if
            the media is created in foreground.
        """
        raise NotImplementedError

    def finalize(self, path=None):
        """
        Ensure the generated thumbnail or preview have been uploaded to the
        Shotgun Server if that was not done during the generate() pass.

        :param path: Path to the media for which thumbnail or/and preview need
            to be uploaded to Shotgun. If None is pass, all jobs will be
            finalized.
        :return: Backburner job IDs created.
        """
        raise NotImplementedError
