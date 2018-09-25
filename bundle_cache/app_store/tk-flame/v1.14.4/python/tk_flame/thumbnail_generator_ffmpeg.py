# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Thumbnail generator based on FFmpeg and read_frame.
"""

__all__ = ["ThumbnailGeneratorFFmpeg"]

from .thumbnail_generator import ThumbnailGenerator

class ThumbnailGeneratorFFmpeg(ThumbnailGenerator):

    def __init__(self, engine):
        super(ThumbnailGeneratorFFmpeg, self).__init__(engine)
        self._job_ids = []

    """
    Thumbnail generator based on ffmpeg and read_frame.
    """
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
        self.engine.log_debug("Create and Upload Preview using ffmpeg")
        job_context = "Create and Upload Shotgun Preview"
        job_name = "%s - %s" % (display_name, job_context)
        job_description = "%s for %s" % (job_context, path)
        job_id = self.engine.create_local_backburner_job(
            job_name,
            job_description,
            dependencies,
            "backburner_hooks",
            "attach_mov_preview",
            {
                "targets": target_entities,
                "width": asset_info["width"],
                "height": asset_info["height"],
                "path": path,
                "display_name": display_name,
                "fps": asset_info["fps"]
            }
        )
        self._job_ids.append(job_id)

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
        self.engine.log_debug("Create and Upload Thumbnail using ffmpeg")
        job_context = "Create and Upload Shotgun Thumbnail"
        job_name = "%s - %s" % (display_name, job_context)
        job_description = "%s for %s" % (job_context, path)
        job_id = self.engine.create_local_backburner_job(
            job_name,
            job_description,
            dependencies,
            "backburner_hooks",
            "attach_jpg_preview",
            {
                "targets": target_entities,
                "width": asset_info["width"],
                "height": asset_info["height"],
                "path": path,
                "display_name": display_name
            }
        )
        self._job_ids.append(job_id)

    def finalize(self, path=None):
        """
        Ensure the generated thumbnail or preview have been uploaded to the
        Shotgun Server if that was not done during the generate() pass.

        :param path: Path to the media for which thumbnail or/and preview need
            to be uploaded to Shotgun. If None is pass, all jobs will be
            finalized.
        :return: Backburner job IDs created.
        """
        job_ids = self._job_ids
        self._job_ids = []
        return job_ids
