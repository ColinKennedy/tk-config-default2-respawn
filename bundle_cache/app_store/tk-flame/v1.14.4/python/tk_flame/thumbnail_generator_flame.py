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
Thumbnail generator based on Flame export API.
"""

__all__ = ["ThumbnailGeneratorFlame"]

from .thumbnail_generator import ThumbnailGenerator

class ThumbnailGeneratorFlame(ThumbnailGenerator):
    """
    Thumbnail generator based on Flame export API
    """

    def __init__(self, engine):
        super(ThumbnailGeneratorFlame, self).__init__(engine)
        self._preview_jobs = {}
        self._thumbnail_jobs = {}

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

        preview_job = self._preview_jobs.get(path, None)
        if preview_job is None:
            self.engine.log_debug("Create and Upload Preview using Flame exporter")

            (dst_path, job_id, files_to_delete) = self.engine.transcoder.transcode(
                src_path=path,
                dst_path=None,
                extension=".mov",
                display_name=display_name,
                job_context="Create Shotgun Preview",
                preset_path=self.engine.previews_preset_path,
                asset_info=asset_info,
                dependencies=dependencies,
                poster_frame=None
            )

            self._preview_jobs[path] = {
                "display_name": display_name,
                "dependencies": job_id,
                "target_entities": target_entities,
                "path": dst_path,
                "files_to_delete": files_to_delete
            }
        else:
            preview_job["target_entities"] = preview_job["target_entities"] + target_entities

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
        thumbnail_job = self._thumbnail_jobs.get(path, None)
        if thumbnail_job is None:
            self.engine.log_debug("Create and Upload Thumbnail using Flame exporter")

            # FIXME we should use the poster frame index supplied by Flame.
            poster_frame = 1

            (dst_path, job_id, files_to_delete) = self.engine.transcoder.transcode(
                src_path=path,
                dst_path=None,
                extension=".jpg",
                display_name=display_name,
                job_context="Create Shotgun Thumbnail",
                preset_path=self.engine.thumbnails_preset_path,
                asset_info=asset_info,
                dependencies=dependencies,
                poster_frame=poster_frame
            )

            self._thumbnail_jobs[path] = {
                "display_name": display_name,
                "dependencies": job_id,
                "target_entities": target_entities,
                "path": dst_path,
                "files_to_delete": files_to_delete
            }
        else:
            thumbnail_job["target_entities"] = thumbnail_job["target_entities"] + target_entities

    def _upload_thumbnail_job(self, thumbnail_job):
        """
        Create a Backburner job to upload a thumbnail and link it to entities.

        :param thumbnail_job: Thumbnail generation job information.
        :return: Backburner job ID created.
        """
        job_context = "Upload Shotgun Thumbnail"
        job_name = "%s - %s" % (thumbnail_job.get("display_name"), job_context)
        job_description = "%s for %s" % (job_context, thumbnail_job.get("path"))
        return self.engine.create_local_backburner_job(
            job_name=job_name,
            description=job_description,
            dependencies=thumbnail_job.get("dependencies"),
            instance="backburner_hooks",
            method_name="upload_to_shotgun",
            args={
                "targets": thumbnail_job.get("target_entities"),
                "path": thumbnail_job.get("path"),
                "field_name": "thumb_image",
                "display_name": thumbnail_job.get("display_name"),
                "files_to_delete": thumbnail_job.get("files_to_delete")
            }
        )

    def _upload_preview_job(self, preview_job):
        """
        Create a Backburner job to upload a preview and link it to entities.

        :param preview_job: Preview generation job information.
        :return: Backburner job ID created.
        """
        if self.engine.get_setting("bypass_server_transcoding"):
            self.engine.log_debug("Bypass Shotgun transcoding setting ENABLED.")
            field_name = "sg_uploaded_movie_mp4"
        else:
            field_name = "sg_uploaded_movie"

        job_context = "Upload Shotgun Preview"
        job_name = "%s - %s" % (preview_job.get("display_name"), job_context)
        job_description = "%s for %s" % (job_context, preview_job.get("path"))
        return self.engine.create_local_backburner_job(
            job_name=job_name,
            description=job_description,
            dependencies=preview_job.get("dependencies"),
            instance="backburner_hooks",
            method_name="upload_to_shotgun",
            args={
                "targets": preview_job.get("target_entities"),
                "path": preview_job.get("path"),
                "field_name": field_name,
                "display_name": preview_job.get("display_name"),
                "files_to_delete": preview_job.get("files_to_delete")
            }
        )

    def finalize(self, path=None):
        """
        Ensure the generated thumbnail or preview have been uploaded to the
        Shotgun Server if that was not done during the generate() pass.

        :param path: Path to the media for which thumbnail or/and preview need
            to be uploaded to Shotgun. If None is pass, all jobs will be
            finalized.
        :return: Backburner job IDs created.
        """

        # A Given path can have both a thumbnail or a preview to upload since
        # not all entity type support a preview upload

        job_ids = []
        if path is not None:
            thumbnail_job = self._thumbnail_jobs.pop(path, None)
            if thumbnail_job is not None:
                job_ids.append(self._upload_thumbnail_job(thumbnail_job))

            preview_job = self._preview_jobs.pop(path, None)
            if preview_job is not None:
                job_ids.append(self._upload_preview_job(preview_job))
        else:
            for thumbnail_job in self._thumbnail_jobs.values():
                job_ids.append(self._upload_thumbnail_job(thumbnail_job))
            self._thumbnail_jobs = {}

            for preview_job in self._preview_jobs.values():
                job_ids.append(self._upload_preview_job(preview_job))
            self._preview_jobs = {}

        return job_ids
