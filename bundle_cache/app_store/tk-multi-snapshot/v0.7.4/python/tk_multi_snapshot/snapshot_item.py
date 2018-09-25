# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import tank
from tank.platform.qt import QtGui, QtCore

browser_widget = tank.platform.import_framework("tk-framework-widget", "browser_widget")

class SnapshotItem(browser_widget.ListItem):
    """
    Extend ListItem to provide additional functionality for a snapshot
    """
    def __init__(self, app, worker, parent = None):
        browser_widget.ListItem.__init__(self, app, worker, parent)
    
        self._path = ""
        
        # tweak UI size:
        #self.geometry()
        
    # @property
    def __get_path(self):
        """
        Property contains the file path for the snapshot
        it represents
        """
        return self._path
    # @path.setter
    def __set_path(self, value):
        self._path = value
    path=property(__get_path, __set_path)
        
        
        
    
    