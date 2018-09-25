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
Local movie generator based on FFMpeg and read_frame.
"""

__all__ = ["LocalMovieGeneratorFFmpeg"]

from .local_movie_generator import LocalMovieGenerator

class LocalMovieGeneratorFFmpeg(LocalMovieGenerator):
    """
    Local movie generator based on FFMpeg and read_frame.
    """

    def __init__(self, engine):
        super(LocalMovieGeneratorFFmpeg, self).__init__(engine)

    def _generate(self, src_path, dst_path, display_name, target_entities, asset_info, dependencies):
        """
        Generate a thumbnail or a preview for a given media asset and link
        it to a list of Shotgun entities. Multiple call to this method with
        same path but different target_entitie can be done to bundle jobs.

        :param src_path: Path to the media for which a local movie need to be generated and linked to Shotgun.
        :param dst_path: Path to local movie file to generate.
        :param display_name: The display name of the item we are generating the
            movie for. This will usually be the based name of the path.
        :param target_entities: Target entities to which the movie need to
            be linked to.
        :param asset_info: Dictionary of attribute passed by Flame's python
            hooks collected either thru an export (sg_export_hooks.py) or a
            batch render (sg_batch_hooks.py).
        :param dependencies: List of backburner job IDs this thumbnail
            generation job need to wait in order to be started. Can be None if
            the media is created in foreground.
        """
        raise NotImplementedError
