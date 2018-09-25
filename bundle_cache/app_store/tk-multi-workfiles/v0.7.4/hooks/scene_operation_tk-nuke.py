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
import nuke

import tank
from tank import Hook
from tank import TankError
from tank.platform.qt import QtGui

class SceneOperation(Hook):
    """
    Hook called to perform an operation with the current scene.
    """
    def execute(self, *args, **kwargs):
        """
        Main hook entry point
        
        :param operation:       String
                                Scene operation to perform
        
        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)
                    
        :param context:         Context
                                The context the file operation is being
                                performed in.
                    
        :param parent_action:   This is the action that this scene operation is
                                being executed for.  This can be one of:
                                - open_file
                                - new_file
                                - save_file_as 
                                - version_up
                        
        :param file_version:    The version/revision of the file to be opened.  If this is 'None'
                                then the latest version should be opened.
        
        :param read_only:       Specifies if the file should be opened read-only or not
                            
        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                'reset'        - True if scene was reset to an empty 
                                                 state, otherwise False
                                all others     - None
        """
        engine = self.parent.engine
        if hasattr(engine, "hiero_enabled") and engine.hiero_enabled:
            return self._hiero_execute(*args, **kwargs)
        elif hasattr(engine, "studio_enabled") and engine.studio_enabled:
            return self._studio_execute(*args, **kwargs)
        else:
            return self._nuke_execute(*args, **kwargs)

    def _studio_execute(self, operation, file_path, context, parent_action, file_version, read_only, **kwargs):
        """
        The Nuke Studio specific scene operations.
        """
        # Out of the box, we treat Nuke Studio just like Hiero, so we
        # can just call through.
        return self._hiero_execute(
            operation,
            file_path,
            context,
            parent_action,
            file_version,
            read_only,
            **kwargs
        )

    def _hiero_execute(self, operation, file_path, context, parent_action, file_version, read_only, **kwargs):
        """
        The Hiero specific scene operations.
        """
        import hiero

        if operation == "current_path":
            # return the current script path
            project = self._get_current_project()
            curr_path = project.path().replace("/", os.path.sep)
            return curr_path
        elif operation == "open":
            # Manually fire the kBeforeProjectLoad event in order to work around a bug in Hiero.
            # The Foundry has logged this bug as:
            #   Bug 40413 - Python API - kBeforeProjectLoad event type is not triggered 
            #   when calling hiero.core.openProject() (only triggered through UI)
            # It exists in all versions of Hiero through (at least) v1.9v1b12. 
            #
            # Once this bug is fixed, a version check will need to be added here in order to 
            # prevent accidentally firing this event twice. The following commented-out code
            # is just an example, and will need to be updated when the bug is fixed to catch the 
            # correct versions.
            # if (hiero.core.env['VersionMajor'] < 1 or 
            #     hiero.core.env['VersionMajor'] == 1 and hiero.core.env['VersionMinor'] < 10:
            hiero.core.events.sendEvent("kBeforeProjectLoad", None)

            # open the specified script
            hiero.core.openProject(file_path.replace(os.path.sep, "/"))
        elif operation == "save":
            # save the current script:
            project = self._get_current_project()
            project.save()
        elif operation == "save_as":
            project = self._get_current_project()
            project.saveAs(file_path.replace(os.path.sep, "/"))
        elif operation == "reset":
            # do nothing and indicate scene was reset to empty
            return True
        elif operation == "prepare_new":
            # add a new project to hiero
            hiero.core.newProject()
    
    def _nuke_execute(self, operation, file_path, context, parent_action, file_version, read_only, **kwargs):
        """
        The Nuke specific scene operations.
        """
        if file_path:
            file_path = file_path.replace("/", os.path.sep)
        
        if operation == "current_path":
            # return the current script path
            return nuke.root().name().replace("/", os.path.sep)
        elif operation == "open":
            # open the specified script
            nuke.scriptOpen(file_path)
            
            # reset any write node render paths:
            if self._reset_write_node_render_paths():
                # something changed so make sure to save the script again:
                nuke.scriptSave()
        elif operation == "save":
            # save the current script:
            nuke.scriptSave()
        elif operation == "save_as":
            old_path = nuke.root()["name"].value()
            try:
                # rename script:
                nuke.root()["name"].setValue(file_path)
                
                # reset all write nodes:
                self._reset_write_node_render_paths()
                        
                # save script:
                nuke.scriptSaveAs(file_path, -1)    
            except Exception, e:
                # something went wrong so reset to old path:
                nuke.root()["name"].setValue(old_path)
                raise TankError("Failed to save scene %s", e)
        elif operation == "reset":
            """
            Reset the scene to an empty state
            """
            while nuke.root().modified():
                # changes have been made to the scene
                res = QtGui.QMessageBox.question(None,
                                                 "Save your script?",
                                                 "Your script has unsaved changes. Save before proceeding?",
                                                 QtGui.QMessageBox.Yes|QtGui.QMessageBox.No|QtGui.QMessageBox.Cancel)
            
                if res == QtGui.QMessageBox.Cancel:
                    return False
                elif res == QtGui.QMessageBox.No:
                    break
                else:
                    nuke.scriptSave()

            # now clear the script:
            nuke.scriptClear()
            return True

    def _get_current_project(self):
        """
        Returns the current project based on where in the UI the user clicked 
        """
        import hiero
        # get the menu selection from hiero engine
        selection = self.parent.engine.get_menu_selection()

        if len(selection) != 1:
            raise TankError("Please select a single Project!")
        
        if not isinstance(selection[0] , hiero.core.Bin):
            raise TankError("Please select a Hiero Project!")
            
        project = selection[0].project()
        if project is None:
            # apparently bins can be without projects (child bins I think)
            raise TankError("Please select a Hiero Project!")
         
        return project
        
    def _reset_write_node_render_paths(self):
        """
        Use the tk-nuke-writenode app interface to find and reset
        the render path of any Tank write nodes in the current script
        """
        write_node_app = self.parent.engine.apps.get("tk-nuke-writenode")
        if not write_node_app:
            return False

        # only need to forceably reset the write node render paths if the app version
        # is less than or equal to v0.1.11
        from distutils.version import LooseVersion
        if (write_node_app.version == "Undefined" 
            or LooseVersion(write_node_app.version) > LooseVersion("v0.1.11")):
            return False
        
        write_nodes = write_node_app.get_write_nodes()
        for write_node in write_nodes:
            write_node_app.reset_node_render_path(write_node)
            
        return len(write_nodes) > 0      
        