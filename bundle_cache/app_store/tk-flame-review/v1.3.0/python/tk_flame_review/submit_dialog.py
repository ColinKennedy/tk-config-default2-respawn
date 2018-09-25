# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk.platform.qt import QtCore, QtGui
from .ui.submit_dialog import Ui_SubmitDialog

class SubmitDialog(QtGui.QWidget):
    """
    Review submission dialog appearing before the export.
    """
    
    def __init__(self):
        """
        Constructor
        """
        # first, call the base class and let it do its thing.
        QtGui.QWidget.__init__(self)
        
        # now load in the UI that was created in the UI designer
        self.ui = Ui_SubmitDialog() 
        self.ui.setupUi(self) 
        
        # with the tk dialogs, we need to hook up our modal 
        # dialog signals in a special way
        self.__exit_code = QtGui.QDialog.Rejected
        self.ui.submit.clicked.connect(self._on_submit_clicked)
        self.ui.cancel.clicked.connect(self._on_cancel_clicked)
        
    @property
    def exit_code(self):
        """
        Used to pass exit code back though sgtk dialog
        
        :returns:    The dialog exit code
        """
        return self.__exit_code
        
    def get_comments(self):
        """
        Returns the comments entered by the user
        
        :returns: comments as string
        """
        return self.ui.comments.toPlainText()
        
    def _on_submit_clicked(self):
        """
        Called when the 'submit' button is clicked.
        """
        self.__exit_code = QtGui.QDialog.Accepted
        self.close()
        
    def _on_cancel_clicked(self):
        """
        Called when the 'cancel' button is clicked.
        """
        self.__exit_code = QtGui.QDialog.Rejected
        self.close()
