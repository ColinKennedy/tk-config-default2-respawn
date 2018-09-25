# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from sgtk import Hook


class HieroPreExport(Hook):
    """
    This class implements a hook that can be used to run custom logic prior to
    the start if the export process.
    """
    def execute(self, processor, **kwargs):
        """
        Called just prior to export. One use case for would be to clear
        cached data here, just before the export begins.

        :param processor: The processor object that is about to be started.
        """
        pass
