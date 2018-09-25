# Copyright (c) 2015 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.     

"""
Hook run by the create Mari project app after a Mari project is created.
"""

import sgtk
from sgtk import TankError

import mari

HookBaseClass = sgtk.get_hook_baseclass()


class PostProjectCreationHook(HookBaseClass):

    def post_project_creation(self, sg_publish_data):
        """
        Run some commands after a project was created.

        :param sg_publish_data: A list of the Shotgun publish records that were
                                used to initialize the new project.
        """

        return
