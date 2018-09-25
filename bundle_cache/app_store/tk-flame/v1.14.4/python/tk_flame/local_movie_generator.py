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
Abstract interface of a local movie generator of Flame's exported assets.
"""

__all__ = ["LocalMovieGenerator"]

class LocalMovieGenerator(object):
    """
    Abstract interface of a local movie generator of Flame's exported assets.
    """

    def __init__(self, engine):
        self._engine = engine

    @property
    def engine(self):
        """
        :returns the DCC engine:
        """
        return self._engine

    def generate(self, src_path, dst_path, display_name, target_entities, asset_info, dependencies):
        """
        Generate a local movie file from a Flame exported assets and link
        it to a list of Shotgun entities in the Path to movie field.

        :param src_path: Path to the media for which a local movie need to be
            generated and linked to Shotgun.
        :param dst_path: Path to local movie file to generate.
        :param display_name: The display name of the item we are generating the
            movie for. This will usually be the based name of the path.
        :param target_entities: Target entities to which the movie need to
            be linked to.
        :param asset_info: Dictionary of attribute passed by Flame's python
            hooks collected either thru an export (sg_export_hooks.py) or a
            batch render (sg_batch_hooks.py).
        :param dependencies: List of backburner job IDs this movie file
            generation job need to wait in order to be started. Can be None if
            the media is created in foreground.
        """
        if not self.engine.get_setting("generate_local_movies"):
            return

        (dst_path, job_id, files_to_delete) = self._generate(
            src_path=src_path,
            dst_path=dst_path,
            display_name=display_name,
            target_entities=target_entities,
            asset_info=asset_info,
            dependencies=dependencies
        )

        self.engine.create_local_backburner_job(
            job_name="%s - Updating Shotgun Path to movie" % display_name,
            description="Uploading Shotgun Path to movie to %s" % dst_path,
            dependencies=job_id,
            instance="backburner_hooks",
            method_name="update_path_to_movie",
            args={
                "targets": target_entities,
                "path": dst_path,
                "files_to_delete": files_to_delete
            }
        )

    def _generate(self, src_path, dst_path, display_name, target_entities, asset_info, dependencies):
        """
        Implmentation of the generator. See generate() for details.
        """
        raise NotImplementedError
