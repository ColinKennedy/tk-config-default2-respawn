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
from tank.platform.qt import QtCore, QtGui

from .string_utils import safe_to_string

thumbnail_widget = tank.platform.import_framework("tk-framework-widget", "thumbnail_widget")

class ThumbnailWidget(thumbnail_widget.ThumbnailWidget):
    pass

class SnapshotForm(QtGui.QWidget):
    """
    Main snapshot UI
    """
    
    # signal emitted when user clicks the 'Create Snapshot' button
    snapshot = QtCore.Signal(QtGui.QWidget, basestring)
    
    SHOW_HISTORY_RETURN_CODE = 2
    
    def __init__(self, file_path, thumbnail, setup_cb, parent = None):
        """
        Construction
        """
        QtGui.QWidget.__init__(self, parent)
    
        self._path = file_path
    
        # set up the UI
        from .ui.snapshot_form import Ui_SnapshotForm
        self._ui = Ui_SnapshotForm()
        self._ui.setupUi(self)

        self._ui.thumbnail_widget.thumbnail = thumbnail
        self._exit_code = QtGui.QDialog.Rejected

        self._ui.snapshot_btn.clicked.connect(self._on_do_snapshot)        
        self._ui.cancel_btn.clicked.connect(self._on_do_cancel)
        self._ui.close_btn.clicked.connect(self._on_do_close)
        self._ui.history_btn.clicked.connect(self._on_show_history)

        # ensure snapshot page is shown first:
        self._ui.page_stack.setCurrentWidget(self._ui.snapshot_page)

        # set focus proxy to the comment edit (first in order)        
        self.setFocusProxy(self._ui.comment_edit)
        
        # want to intercept 'enter' key pressed in the comment edit:
        self._ui.comment_edit.keyPressEvent = lambda e, df=self._ui.comment_edit.keyPressEvent: self._on_comment_edit_key_pressed(df, e)
        
        # finally, run setup callback to allow caller to connect 
        # up signals etc.
        setup_cb(self)
            
    @property
    def exit_code(self):
        """
        Used to pass exit code back though tank dialog
        """
        return self._exit_code
    
    @property
    def thumbnail(self):
        return self._ui.thumbnail_widget.thumbnail
    
    @property
    def comment(self):
        return safe_to_string(self._ui.comment_edit.toPlainText()).rstrip()
        
    def show_result(self, status, msg):
        """
        Show the result page
        """
        self._ui.page_stack.setCurrentWidget(self._ui.status_page)
        self._ui.status_title.setText(["Oh No, Something Went Wrong!", "Success!"][status])
        self._ui.status_details.setText([msg, "Snapshot Successfully Created"][not msg])
        self._ui.status_icon.setPixmap(QtGui.QPixmap([":/res/failure.png", ":/res/success.png"][status]))

        # In later versions of Foundry software (like Hiero 9.0) we
        # have issues with some scene operations forcing their window
        # to the foreground, so we'll make sure to raise ours back
        # in front.
        self.window().raise_()
        
    def _on_comment_edit_key_pressed(self, default_func, event):
        """
        Custom override of the comment edit keyPressEvent function.
        Allows us to trap the 'Enter' key press so that we can do
        a snapshot instead of a new line!
        """
        # check for enter key being pressed:
        if event.key() == QtCore.Qt.Key_Return:
            self._on_do_snapshot()
        elif default_func:
            return default_func(event)
        
    def _on_do_cancel(self):
        self._exit_code = QtGui.QDialog.Rejected
        self.close()

    def _on_do_close(self):
        self._exit_code = QtGui.QDialog.Accepted
        self.close()
    
    def _on_do_snapshot(self):
        # emit signal to do snapshot:
        self.snapshot.emit(self, self._path)    
        
    def _on_show_history(self):
        self._exit_code = SnapshotForm.SHOW_HISTORY_RETURN_CODE
        self.close()
                
    