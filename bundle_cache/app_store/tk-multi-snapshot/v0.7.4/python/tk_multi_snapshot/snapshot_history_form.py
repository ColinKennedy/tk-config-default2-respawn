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
from tank.platform.qt import QtCore, QtGui

class SnapshotHistoryForm(QtGui.QWidget):
    
    restore = QtCore.Signal(QtGui.QWidget, basestring, basestring)
    snapshot = QtCore.Signal(QtGui.QWidget)
    closed = QtCore.Signal(QtGui.QWidget)
    
    def __init__(self, app, handler, parent = None):
        """
        Construction
        """
        QtGui.QWidget.__init__(self, parent)
    
        self._app = app
        self._handler = handler

        self._path = ""
    
        # set up the UI
        from .ui.snapshot_history_form import Ui_SnapshotHistoryForm
        self._ui = Ui_SnapshotHistoryForm()
        self._ui.setupUi(self)
        
        self._ui.snapshot_list.set_app(self._app)
        self._ui.snapshot_list.selection_changed.connect(self._on_list_selection_changed)
        
        self._ui.snapshot_list.action_requested.connect(self._on_restore)
        self._ui.restore_btn.clicked.connect(self._on_restore)
        
        self._ui.snapshot_btn.clicked.connect(self._on_snapshot_btn_clicked)
        
    @property
    def path(self):
        return self._path
            
    def refresh(self):
        # clear the snapshot list:
        self._ui.snapshot_list.clear()
        
        # get the current path from the handler:
        self._path = None
        try:
            self._path = self._handler.get_current_file_path()
        except Exception, e:
            # this only ever happens when the scene operation hook
            # throws an exception!
            msg = ("Failed to find the current work file path:\n\n"
                  "%s\n\n"
                  "Unable to continue!" % e)
            self._ui.snapshot_list.set_message(msg)
            return
        
        # load file list:
        self._ui.snapshot_list.load({"handler":self._handler,
                                     "file_path":self._path})
        
        # update the browser title:
        self._ui.snapshot_list.set_label(self._handler.get_history_display_name(self._path))
        
    def closeEvent(self, event):
        """
        Called when the widget is closed.
        """
        # make sure the snapshot list BrowserWidget is 
        # cleaned up properly
        self._ui.snapshot_list.destroy()
        
        # emit closed event:
        self.closed.emit(self)
        
        return QtGui.QWidget.closeEvent(self, event)
              
    def event(self, event):
        """
        override event to cause UI to reload the first time it is shown:
        """
        if event.type() == QtCore.QEvent.Polish:
            self.refresh()
        return QtGui.QWidget.event(self, event)

    def _on_list_selection_changed(self):
        self._update_ui()
        
    def _on_restore(self):
        path = self._ui.snapshot_list.get_selected_path()
        self.restore.emit(self, self._path, path)
        
    def _on_snapshot_btn_clicked(self):
        self.snapshot.emit(self)
        
    def _update_ui(self):
        can_restore = self._ui.snapshot_list.get_selected_item() != None
        self._ui.restore_btn.setEnabled(can_restore)
        


    