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
import photoshop

from tank import Hook
from tank import TankError

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
                    all others     - None
        """
        
        if operation == "current_path":
            # return the current script path
            
            doc = self._get_active_document()
            if doc.fullName is None:
                # not saved?
                path = ""
            else:
                path = doc.fullName.nativePath
            
            return path
        
        elif operation == "open":
            # reopen the specified script
            
            doc = self._get_active_document()
            doc.close()            
            f = photoshop.RemoteObject('flash.filesystem::File', file_path)
            photoshop.app.load(f)            

        elif operation == "save":
            # save the current script:
            doc = self._get_active_document()
            doc.save()


    def _get_active_document(self):
        """
        Returns the currently open document in Photoshop.
        Raises an exeption if no document is active.
        """
        doc = photoshop.app.activeDocument
        if doc is None:
            raise TankError("There is no currently active document!")
        return doc