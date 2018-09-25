# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Project management app for Mari that augments Mari's own project management 
functionality so that projects are Toolkit aware
"""

from sgtk import TankError
from sgtk.platform import Application

class MariProjectManager(Application):
    """
    The main app instance
    """

    def init_app(self):
        """
        Called as the app is being initialized
        """
        self.log_debug("%s: Initializing..." % self)
        
        # register the start new project command:
        self.engine.register_command("New Project...", self.start_new_project_ui)

        tk_mari_projectmanager = self.import_module("tk_mari_projectmanager")
        self.__project_mgr = tk_mari_projectmanager.ProjectManager(self)

    def destroy_app(self):
        """
        Called when the app is being destroyed
        """
        self.log_debug("%s: Destroying..." % self)

    def start_new_project_ui(self):
        """
        Show the New Project UI
        """
        # find the loader app - this is required so that we can browse for publishes:
        loader_app = self.engine.apps.get("tk-multi-loader2")
        if not loader_app:
            raise TankError("Unable to start new project - the tk-multi-loader2 app needs to be "
                            "available in the current environment!") 
        
        # show the dialog:
        self.__project_mgr.show_new_project_dialog()

    def create_new_project(self, sg_publish_data, name = None):
        """
        Utility method to create a new project with the specified Shotgun publishes using
        the settings provided for the app.
        
        :param sg_publish_data: A list of Shotgun publish records for the published geometry
                                that should be loaded into the new project.  At least one
                                valid publish must be specified.
        :param name:            The name to use when constructing the project name using
                                the new project name template defined in the settings
        :returns:               The new Mari Project instance if successful
        """
        return self.__project_mgr.create_new_project(name, sg_publish_data)

