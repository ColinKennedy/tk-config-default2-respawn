# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import tank
import os
import sys
import threading

from tank.platform.qt import QtCore, QtGui

def start_qt_app_and_show_modal(title, engine, widget_class, *args, **kwargs):
    """
    Wrapper around the engine.show_modal() call that first starts a 
    QApplication, then shows the window, then quits the QApplication.
    
    :param title: Window title
    :param engine: Engine object to associate with
    :param widget_class: UI class to create
    :param args/kwargs: parameters to pass to the UI
    
    :returns: The modal dialog return value
    """
    
    t = QtTask(title, engine, widget_class, args, kwargs)
    
    # start up our QApp now
    qt_application = QtGui.QApplication([])
    qt_application.setWindowIcon(QtGui.QIcon(engine.icon_256))
    engine._initialize_dark_look_and_feel()
    
    # when the QApp starts, initialize our task code 
    QtCore.QTimer.singleShot(0, t.run_command)
       
    # and ask the main app to exit when the task emits its finished signal
    t.finished.connect(qt_application.quit)
       
    # start the application loop. This will block the process until the task
    # has completed - this is either triggered by a main window closing or
    # by the finished signal being called from the task class above.
    qt_application.exec_()
    
    return t.get_return_data()

class QtTask(QtCore.QObject):
    """
    QT dialogue wrapper
    """
    finished = QtCore.Signal()

    def __init__(self, title, engine, widget_class, args, kwargs):
        """
        Constructor
        """
        QtCore.QObject.__init__(self)        
        self._title = title
        self._engine = engine
        self._widget_class = widget_class
        self._args = args
        self._kwargs = kwargs
        self._return_data = None
        
    def run_command(self):
        """
        Execute the payload of the task. Emit finished signal at the end.
        """
        try:
            # execute the callback
            self._return_data = self._engine.show_modal(self._title, 
                                                        self._engine, 
                                                        self._widget_class, 
                                                        *self._args, 
                                                        **self._kwargs)
        
        
        except KeyboardInterrupt:
            self._engine.log_info("The operation was cancelled by the user.")
            
        finally:
            # broadcast that we have finished this command
            self.finished.emit()
            
    def get_return_data(self):
        """
        Return the return value from the modal dialog
        """
        return self._return_data
        
