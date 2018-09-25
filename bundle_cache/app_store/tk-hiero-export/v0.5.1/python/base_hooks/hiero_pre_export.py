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


class HieroPreExport(HookBaseClass):
    """
    This class implements a hook that can be used to run custom logic prior to
    the start if the export process.
    """
    def execute(self, processor, **kwargs):
        """
        Called just prior to export. One use case for would be to clear
        cached data here, just before the export begins.

        :param processor: The processor object that is about to be started.
            Hiero API docs are available `here. <https://learn.foundry.com/hiero/developers/1.8/hieropythondevguide/api/api_core.html#hiero.core.ProcessorBase>`_
        """
        pass
