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


class HieroGetShot(HookBaseClass):
    """
    This class implements a hook that can determines which Shotgun entity
    should be associated with each task and track item being exported.
    """
    def execute(self, task, item, data, **kwargs):
        """
        Takes a hiero.core.TrackItem as input and returns a data dictionary for
        the shot to update the cut info for.

        :param task: The Hiero task being processed. Hiero API docs are
            available `here. <https://learn.foundry.com/hiero/developers/1.8/hieropythondevguide/api/api_core.html#hiero.core.TaskBase>`_
        :param item: The Hiero track item being processed. Hiero API docs
            are available `here. <https://learn.foundry.com/hiero/developers/1.8/hieropythondevguide/api/api_core.html#hiero.core.TrackItem>`_
        :param dict data: A dictionary with cached parent data.

        :returns: A Shot entity.
        :rtype: dict
        """
        pass

    def get_shot_parent(self, hiero_sequence, data, **kwargs):
        """
        Given a Hiero sequence and data cache, return the corresponding entity
        in Shotgun to serve as the parent for contained Shots.

        .. note:: The data dict is typically the app's `preprocess_data` which
            maintains the cache across invocations of this hook.

        :param hiero_sequence: A Hiero sequence object. Hiero API docs are
            available `here. <https://learn.foundry.com/hiero/developers/1.8/hieropythondevguide/api/api_core.html#hiero.core.Sequence>`_
        :param dict data: A dictionary with cached parent data.

        :returns: A Shotgun entity.
        :rtype: dict
        """
        raise NotImplementedError
