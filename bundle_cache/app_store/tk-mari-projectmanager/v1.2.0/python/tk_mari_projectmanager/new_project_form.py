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
UI for creating a new project
"""

import sgtk
from sgtk.platform.qt import QtGui, QtCore

class NewProjectForm(QtGui.QWidget):
    """
    The main UI used when creating a new Mari project
    """
    
    # define signals that this form exposes:
    #
    # emitted when the 'Create Project' button is clicked
    create_project = QtCore.Signal(QtGui.QWidget)
    # emitted when the 'Add Publish' button is clicked
    browse_publishes = QtCore.Signal(QtGui.QWidget)
    # emitted when the user requests to remove publishes from the publish list
    remove_publishes = QtCore.Signal(QtGui.QWidget, list)
    
    def __init__(self, app, init_proc, preview_updater, initial_name, parent=None):
        """
        Construction
        
        :param app:             The current app
        :param init_proc:       Called at the end of construction to allow the calling
                                code to hook up any signals, etc.
        :param preview_updater: A background worker that can be used to update the
                                project name preview
        :param initial_name:    The initial name to use in the name field
        :param parent:          The parent QWidget
        """
        QtGui.QWidget.__init__(self, parent)

        self.__preview_updater = preview_updater
        if self.__preview_updater:
            self.__preview_updater.work_done.connect(self._preview_info_updated)
        
        # set up the UI
        from .ui.new_project_form import Ui_NewProjectForm
        self.__ui = Ui_NewProjectForm()
        self.__ui.setupUi(self)
        
        self.__ui.create_btn.clicked.connect(self._on_create_clicked)
        self.__ui.add_publish_btn.clicked.connect(self._on_add_publish_clicked)
        self.__ui.name_edit.textEdited.connect(self._on_name_edited)
        
        self.__ui.publish_list.set_app(app)
        self.__ui.publish_list.remove_publishes.connect(self._on_remove_selected_publishes)
        
        # Fix line colours to match 75% of the text colour.  If we don't do this they are
        # extremely bright compared to all other widgets!  This also seems to be the only
        # way to override the default style sheet?!
        clr = QtGui.QApplication.palette().text().color()
        clr_str = "rgb(%d,%d,%d)" % (clr.red() * 0.75, clr.green() * 0.75, clr.blue() * 0.75)
        self.__ui.name_line.setStyleSheet("#name_line{color: %s;}" % clr_str)
        self.__ui.publishes_line.setStyleSheet("#publishes_line{color: %s;}" % clr_str)
        self.__ui.break_line.setStyleSheet("#break_line{color: %s;}" % clr_str)        
             
        # initialise the UI:
        self.__ui.name_edit.setText(initial_name)
        self.update_publishes()
        init_proc(self)
        
        # update the name preview:
        if self.__preview_updater:
            self.__preview_updater.do(self.project_name)
        
    @property
    def project_name(self):
        """
        Access the entered project name
        :returns:    The project name the user entered
        """
        return self.__ui.name_edit.text()
    
    def update_publishes(self, sg_publish_data=None):
        """
        Update the list of publishes
        
        :param sg_publish_data: The list of publishes to present.  This is a list of 
                                Shotgun entity dictionaries.
        """
        # clear the existing publishes from the list:
        self.__ui.publish_list.clear()
        if not sg_publish_data:
            # display the error message in the list and siable the create button:
            self.__ui.publish_list.set_message("<i>You must add at least one publish before "
                                               "you can create the new project...</i>")
            self.__ui.create_btn.setEnabled(False)
        else:
            # load the publishes into the list and enable the create button:
            self.__ui.publish_list.load(sg_publish_data)
            self.__ui.create_btn.setEnabled(True)

    def closeEvent(self, event):
        """
        Called when the widget is closed so that any cleanup can be 
        done. Overrides QWidget.clostEvent.
        
        :param event:    The close event.
        """
        # make sure the publish list BrowserWidget is 
        # cleaned up properly
        self.__ui.publish_list.destroy()
        
        # disconnect the preview updater:
        if self.__preview_updater:
            self.__preview_updater.work_done.disconnect(self._preview_info_updated)
        
        # return result from base implementation
        return QtGui.QWidget.closeEvent(self, event)

    def _on_create_clicked(self):
        """
        Called when the user clicks the create button
        """
        self.create_project.emit(self)
        
    def _on_add_publish_clicked(self):
        """
        Called when the user clicks the add publish button
        """
        self.browse_publishes.emit(self)
        
    def _on_name_edited(self, txt):
        """
        Called when the user edits the name
        :param txt:    The current text entered into the edit control
        """
        # if we have a preview updater then update the name
        # preview:
        if self.__preview_updater:
            self.__preview_updater.do(self.project_name)

    def _on_remove_selected_publishes(self, publish_ids):
        """
        Called when the user requests to remove some publishes from the list
        
        :param publish_ids:    The list of publish ids to be removed
        """
        self.remove_publishes.emit(self, publish_ids)

    def _preview_info_updated(self, name, result):
        """
        Called when the worker thread has finished generating the
        new project name
        
        :param name:    The name entered in to the name edit control
        :param result:  The result returned by the worker thread.  This is a dictionary
                        containing the "project_name" and/or the error "message".
        """
        project_name = result.get("project_name")
        if project_name:
            # updat the preview with the project name:
            self.__ui.name_preview_label.setText("<b>%s</b>" % project_name)
        else:
            # updat the preview with the error message:
            message = result.get("message", "")
            warning = "<p style='color:rgb(226, 146, 0)'>%s</p>" % message
            self.__ui.name_preview_label.setText(warning)

    