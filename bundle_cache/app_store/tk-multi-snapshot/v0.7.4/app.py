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
Multi Publish

"""

import os
import tank
from tank import TankError

class MultiSnapshot(tank.platform.Application):

    def init_app(self):
        """
        Called as the application is being initialized
        """
        self.tk_multi_snapshot = self.import_module("tk_multi_snapshot")
      
        # ensure snapshot template has at least one of increment or timestamp:
        snapshot_template = self.get_template("template_snapshot")
        if (not "timestamp" in snapshot_template.keys
            and not "increment" in snapshot_template.keys):
            self.log_error("'template_snapshot' must contain at least one of 'timestamp' or 'increment'")
            return
      
        # register commands:

        self.engine.register_command(
            "Snapshot...",
            self.show_snapshot_dlg,
            {
                # dark themed icon for engines that recognize this format
                "icons": {
                    "dark": {
                        "png": os.path.join(
                            os.path.dirname(__file__),
                            "resources",
                            "snapshot_menu_icon.png"
                        )
                    }
                }
            }
        )

        self.engine.register_command(
            "Snapshot History...",
            self.show_snapshot_history_dlg,
            {
                # dark themed icon for engines that recognize this format
                "icons": {
                    "dark": {
                        "png": os.path.join(
                            os.path.dirname(__file__),
                            "resources",
                            "snapshot_history_menu_icon.png"
                        )
                    }
                }
            }
        )

    @property
    def context_change_allowed(self):
        """
        Specifies that context changes are allowed.
        """
        return True
        
    def destroy_app(self):
        self.tk_multi_snapshot = None
        self.log_debug("Destroying tk-multi-snapshot")
        
    def show_snapshot_dlg(self):
        """
        Shows the Snapshot Dialog.
        """
        return self.tk_multi_snapshot.Snapshot(self).show_snapshot_dlg()

    def show_snapshot_history_dlg(self):
        """
        Shows the Snapshot History Dialog.
        """
        self.tk_multi_snapshot.Snapshot(self).show_snapshot_history_dlg()

    def can_snapshot(self, work_path=None):
        """
        Helper method to determine if a snapshot can be made with work_path.
        """
        return self.tk_multi_snapshot.Snapshot(self).can_snapshot(work_path)

    def snapshot(self, comment=None, thumbnail=None):
        """
        Snapshots the current scene without any UI
        """
        handler = self.tk_multi_snapshot.Snapshot(self)
        work_path = handler.get_current_file_path()
        return handler.do_snapshot(work_path, thumbnail, comment)
    
    
    