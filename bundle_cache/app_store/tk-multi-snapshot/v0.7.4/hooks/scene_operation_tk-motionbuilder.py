# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
from pyfbsdk import FBApplication

import sgtk
from sgtk import Hook
from sgtk import TankError
from sgtk.platform.qt import QtGui

class SceneOperation(Hook):
    """
    Hook called to perform an operation with the
    current scene
    """

    def execute(self, operation, file_path, **kwargs):
        """
        Main hook entry point
        
        :param operation:       String
                                Scene operation to perform
        
        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)
                    
        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                all others     - None
        """
        
        fb_app = FBApplication()

        if operation == "current_path":
            # return the current scene path
            return fb_app.FBXFileName
        elif operation == "open":
            # do new scene as Maya doesn't like opening
            # the scene it currently has open!
            fb_app.FileOpen( file_path )
        elif operation == "save":
            # save the current scene:
            # Note - have to pass the current scene name to
            # avoid showing the save-as dialog
            fb_app.FileSave(fb_app.FBXFileName)