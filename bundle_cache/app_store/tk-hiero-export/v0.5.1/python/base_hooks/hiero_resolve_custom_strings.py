# Copyright (c) 2018 Shotgun Software Inc.
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


class HieroResolveCustomStrings(HookBaseClass):
    """
    This class implements a hook that is used to resolve custom tokens into
    their concrete value when paths are being processed during the export.
    """
    def execute(self, task, keyword, **kwargs):
        """
        The default implementation of the custom resolver simply looks up
        the keyword from the Shotgun Shot entity dictionary. For example,
        to pull the shot code, you would simply specify 'code'. To pull
        the sequence code you would use 'sg_sequence.Sequence.code'.

        :param task: The export task being processed. Hiero API docs are
            available `here. <https://learn.foundry.com/hiero/developers/1.8/hieropythondevguide/api/api_core.html#hiero.core.TaskBase>`_
        :param str keyword: The keyword token that needs to be resolved.

        :returns: The resolved keyword value to be replaced into the
            associated string.
        :rtype: str
        """
        pass
