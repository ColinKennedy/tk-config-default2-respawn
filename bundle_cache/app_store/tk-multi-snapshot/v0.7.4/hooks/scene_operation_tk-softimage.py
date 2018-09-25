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

import tank
from tank import Hook

import win32com
from win32com.client import Dispatch, constants
from pywintypes import com_error

Application = Dispatch("XSI.Application").Application

class SceneOperation(Hook):
    """
    Hook called to perform an operation with the 
    current scene
    """
    
    def execute(self, operation, file_path, **kwargs):
        """
        Main hook entry point
        
        :operation: String
                    Scene operation to perform
        
        :file_path: String
                    File path to use if the operation
                    requires it (e.g. open)
                    
        :returns:   Depends on operation:
                    'current_path' - Return the current scene
                                     file path as a String
                    'reset'        - True if scene was reset to an empty 
                                     state, otherwise False
                    all others     - None
        """
        
        if operation == "current_path":
            # return the current scene path
            
            # query the current scene 'name' and file path from the application:
            scene_filepath = Application.ActiveProject.ActiveScene.filename.value
            scene_name = Application.ActiveProject.ActiveScene.Name
                        
            # There doesn't seem to be an easy way to determin if the current scene 
            # is 'new'.  However, if the file name is "Untitled.scn" and the scene 
            # name is "Scene" rather than "Untitled", then we can be reasonably sure 
            # that we haven't opened a file called Untitled.scn
            if scene_name == "Scene" and os.path.basename(scene_filepath) == "Untitled.scn":
                return ""
            return scene_filepath

        elif operation == "open":
            # open the specified scene without any prompts
            
            # Redraw the UI
            # Certain OnEndNewScene events can result in Softimage
            # crashing if a scene is opened immediately after doing
            # a new scene.  One such event is the Solid Andle Arnold
            # renderer SITOA_OnEndNewScene event which sets some 
            # viewport settings.
            #
            # Calling RedrawUI seems to force the events to complete
            # before the open and therefore avoids the crash!
            Application.Desktop.RedrawUI()
            
            # Application.OpenScene(path, Confirm, ApplyAuxiliaryData)
            Application.OpenScene(file_path, False, False)

        elif operation == "save":
            # save the current scene:
            Application.SaveScene()

        elif operation == "reset":
            # reset the current scene - for snapshot this is only ever
            # called when restoring from snapshot history prior to
            # opening the restored scene
            try:
                # perform the new scene:
                Application.NewScene("", True)
            except:
                return False
            else:
                return True           
            
            
            
            
            
            
            
            
