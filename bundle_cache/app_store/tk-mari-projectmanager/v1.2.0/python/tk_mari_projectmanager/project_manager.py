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
Manage project creation in a Toolkit aware fashion
"""

from .async_worker import AsyncWorker

import sgtk
from sgtk import TankError
from sgtk.platform.qt import QtGui

import mari

from new_project_form import NewProjectForm

class ProjectManager(object):
    """
    Handle all Mari project management
    """
    
    def __init__(self, app):
        """
        Construction
        
        :param app:    The Application instance that created this instance
        """
        self._app = app
        self.__new_project_publishes = []        
        self.__project_name_template = self._app.get_template("template_new_project_name")
        
    def create_new_project(self, name_part, sg_publish_data):
        """
        Create a new project in the current Toolkit context and seed it
        with the specified geometry
        
        :param name:                The name to use in the project_name template when 
                                    generating the project name
        :param sg_publish_data:     List of the initial geometry publishes to load for 
                                    into the new project.  Each entry in the list is a
                                    Shotgun entity dictionary
        :returns:                   The new Mari project instance if successful or None 
                                    if not
        :raises:                    TankError if something went wrong at any stage!
        """
        # create the project name:
        name_result = self._generate_new_project_name(name_part)
        project_name = name_result.get("project_name")
        if not project_name:
            raise TankError("Failed to determine the project name: %s" % name_result.get("message"))
        
        # use a hook to retrieve the project creation settings to use:
        hook_res = {}
        try:
            hook_res = self._app.execute_hook_method("get_project_creation_args_hook", 
                                                     "get_project_creation_args", 
                                                     sg_publish_data = sg_publish_data)
            if hook_res == None:
                hook_res = {}
            elif not isinstance(hook_res, dict):
                raise TankError("get_project_creation_args_hook returned unexpected type!")
        except TankError, e:
            raise TankError("Failed to get project creation args from hook: %s" % e)
        except Exception, e:
            self._app.log_exception("Failed to get project creation args from hook!")
            raise TankError("Failed to get project creation args from hook: %s" % e)
        
        # extract the options from the hook result:
        channels_to_create = hook_res.get("channels_to_create", [])
        channels_to_import = hook_res.get("channels_to_import", [])
        project_meta_options = hook_res.get("project_meta_options", {})
        objects_to_load = hook_res.get("objects_to_load", [])
        
        # and create the project using the tk-mari engine helper method:
        new_project = self._app.engine.create_project(project_name, 
                                                      sg_publish_data, 
                                                      channels_to_create = channels_to_create, 
                                                      channels_to_import = channels_to_import, 
                                                      project_meta_options = project_meta_options, 
                                                      objects_to_load = objects_to_load)

        try:
            hook_res = self._app.execute_hook_method("post_project_creation_hook", 
                                                     "post_project_creation", 
                                                     sg_publish_data = sg_publish_data)
            if hook_res == None:
                hook_res = {}
            elif not isinstance(hook_res, dict):
                raise TankError("post_project_creation_hook returned unexpected type!")
        except TankError, e:
            raise TankError("Failed to post project creation from hook: %s" % e)
        except Exception, e:
            self._app.log_exception("Failed to post project creation from hook!")
            raise TankError("Failed to post project creation from hook: %s" % e)

        return new_project
        
    def show_new_project_dialog(self):
        """
        Show the new project dialog
        """
        self.__new_project_publishes = []
        default_name = self._app.get_setting("default_project_name")
        
        # create a background worker that will be responsible for updating
        # the project name preview as the user enters a name.
        worker_cb = lambda name: self._generate_new_project_name(name)
        preview_updater = AsyncWorker(worker_cb)
        try:
            preview_updater.start()

            # show modal dialog:            
            res, new_project_form = self._app.engine.show_modal("New Project", self._app, NewProjectForm, 
                                                                self._app, self._init_new_project_form,
                                                                preview_updater, default_name)
        finally:
            # wait for the background thread to finish!
            preview_updater.stop()
        
    def _generate_new_project_name(self, name):
        """
        Generate the new project name using the current context, the provided name and the
        project name template defined for the app.
        
        :param name:    The name the user entered
        :returns:       Dictionary containing "message" and/or "project_name".  If the project
                        name can't be determined then the message should be populated with
                        the reason why
        """
        if not name:
            return {"message":"Please enter a name!"}
        if not self.__project_name_template.keys["name"].validate(name):
            return {"message":"Your name contains illegal characters!"}

        project_name = None        
        try:
            # get fields from the current context"
            fields = self._app.context.as_template_fields(self.__project_name_template)
            # add in the name:
            fields["name"] = name
            # try to create the project name:
            project_name = self.__project_name_template.apply_fields(fields)
        except TankError, e:
            return {"message":"Failed to create project name!"}
        
        if project_name in mari.projects.names():
            return {"message":"A project with this name already exists!"}
        
        return {"project_name":project_name}        
        
    def _init_new_project_form(self, new_project_form):
        """
        Initialise the new project form after it's been created
        
        :param new_project_form:    The new project form to initialise
        """
        # connect to signals:
        new_project_form.create_project.connect(self._on_create_new_project)
        new_project_form.browse_publishes.connect(self._on_browse_for_publishes)
        new_project_form.remove_publishes.connect(self._on_remove_publishes)
        
    def _on_remove_publishes(self, new_project_form, publish_ids):
        """
        Called when user interaction has requested that publishes be removed
        from the publish list:
        
        :param new_project_form:   The new project form to initialise
        :param publish_ids:        List of publish ids to remove
        """
        # remove publishes from the list:
        publishes = []
        for publish in self.__new_project_publishes:
            if publish["id"] in publish_ids:
                continue
            publishes.append(publish)
        self.__new_project_publishes = publishes
        
        # update the list to reflect changes:
        new_project_form.update_publishes(self.__new_project_publishes)
        
    def _on_browse_for_publishes(self, new_project_form):
        """
        Called when the user clicks the 'Add Publishes' button in the new
        project form.  Opens the loader so that the user can select a publish
        to be loaded into the new project.
        
        :param new_project_form:    The new project form that the button was
                                    clicked in
        """
        loader_app = self._app.engine.apps.get("tk-multi-loader2")
        if not loader_app:
            raise TankError("The tk-multi-loader2 app needs to be available to browse for publishes!")
        
        # browse for publishes:
        publish_types = self._app.get_setting("publish_types")
        selected_publishes = loader_app.open_publish("Select Published Geometry", "Select", publish_types)
        
        # make sure we keep this list of publishes unique:
        current_ids = set([p["id"] for p in self.__new_project_publishes])
        for sg_publish in selected_publishes:
            publish_id = sg_publish.get("id")
            if publish_id != None and publish_id not in current_ids:
                current_ids.add(publish_id)
                self.__new_project_publishes.append(sg_publish)
        
        # update new project form with selected geometry:
        new_project_form.update_publishes(self.__new_project_publishes)
        
    def _on_create_new_project(self, new_project_form):
        """
        Called when the user clicks the 'Create Project' button in the new project
        form.  This will create the project and close the form if successful, otherwise
        it will display a message box with the reason the project wasn't created.
        
        :param new_project_form:    The new project form that the button was clicked
                                    in
        """
        try:
            name = new_project_form.project_name
            if self.create_new_project(name, self.__new_project_publishes):
                new_project_form.close()
        except TankError, e:
            QtGui.QMessageBox.information(new_project_form, "Failed to create new project!", "%s" % e)
        except Exception, e:
            QtGui.QMessageBox.information(new_project_form, "Failed to create new project!", "%s" % e)
            self._app.log_exception("Failed to create new project!")















        
    