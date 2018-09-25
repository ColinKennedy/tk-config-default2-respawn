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
from .ui.batch_render_dialog import Ui_BatchRenderDialog

class BatchRenderDialog(QtGui.QWidget):
    """
    UI popping up before a Flare/Batch render happens,
    asking the user if they want to submit the render for 
    review in Shotgun and in that case to enter some comments.
    """
    
    def __init__(self):
        """
        Constructor
        """
        # first, call the base class and let it do its thing.
        QtGui.QWidget.__init__(self)
        
        # now load in the UI that was created in the UI designer
        self.ui = Ui_BatchRenderDialog() 
        self.ui.setupUi(self) 
        
        # with the tk dialogs, we need to hook up our modal 
        # dialog signals in a special way
        self.__exit_code = QtGui.QDialog.Rejected
        self.ui.submit.clicked.connect(self._on_submit_clicked)
        self.ui.cancel.clicked.connect(self._on_cancel_clicked)
        
    @property
    def hide_tk_title_bar(self):
        """
        Tell the system to not show the std toolbar
        """
        return True
        
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
