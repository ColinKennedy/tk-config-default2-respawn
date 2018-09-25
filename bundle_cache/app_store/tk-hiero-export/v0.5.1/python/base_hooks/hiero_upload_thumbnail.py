# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class HieroUploadThumbnail(HookBaseClass):
    """
    This class implements a hook that's responsible for uploading a thumbnail
    to a given Shotgun entity for a given Hiero source item.
    """
    def execute(self, entity, source, item, **kwargs):
        """
        Uploads a thumbnail to the given entity in Shotgun.

        :param dict entity: The entity dictionary that will receive the new
            thumbnail image.
        :param source: The Hiero source sequence object being exported.
        :param item: The Hiero task item being processed.
        :param task: The Hiero task being processed.
        """
        pass
