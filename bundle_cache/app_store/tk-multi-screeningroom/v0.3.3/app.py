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
An app that launches Screening Room

"""

import sys
import os

from tank.platform import Application
from tank import TankError

class MultiLaunchScreeningRoom(Application):
    
    def init_app(self):
        
        if self.get_setting("enable_rv_mode"):        
            self.engine.register_command("Jump to Screening Room in RV", 
                                         self._start_screeningroom_rv,
                                         {"type": "context_menu", "short_name": "screening_room_rv"})
        
        if self.get_setting("enable_web_mode"):        
            self.engine.register_command("Jump to Screening Room Web Player", 
                                         self._start_screeningroom_web,
                                         {"type": "context_menu", "short_name": "screening_room_web"})

    @property
    def context_change_allowed(self):
        """
        Specifies that context changes are allowed.
        """
        return True

    def _get_rv_binary(self):
        """
        Returns the RV binary to run
        """
        # get the setting        
        system = sys.platform
        try:
            app_setting = {"linux2": "rv_path_linux", "darwin": "rv_path_mac", "win32": "rv_path_windows"}[system]
            app_path = self.get_setting(app_setting)
            if not app_path: raise KeyError()
        except KeyError:
            raise TankError("Platform '%s' is not supported." % system) 
        
        if system == "darwin":
            # append Contents/MacOS/RV64 to the app bundle path
            # if that doesn't work, try with just RV, which is used by 32 bit RV
            # if that doesn't work, show an error message
            orig_app_path = app_path
            app_path = os.path.join(orig_app_path, "Contents/MacOS/RV64")
            if not os.path.exists(app_path):
                # try 32 bit RV (which has an RV executable rather than RV64
                app_path = os.path.join(orig_app_path, "Contents/MacOS/RV")
            if not os.path.exists(app_path):
                # did not find rv64 nor 32
                raise Exception("The RV path you have configured ('%s') does not exist!" % orig_app_path)            
        
        return app_path
        
    def _get_entity(self):
        """
        Returns the most relevant playback entity (as a sg std dict) for the current context
        """
        
        # figure out the context for Screening Room
        # first try to get a version
        # if that fails try to get the current entity
        rv_context = None
        task = self.context.task
        if task:
            # look for versions matching this task!
            self.log_debug("Looking for versions connected to %s..." % task)
            filters = [["sg_task", "is", task]]
            order   = [{"field_name": "created_at", "direction": "desc"}]
            fields  = ["id"]
            version = self.shotgun.find_one("Version", 
                                            filters=filters, 
                                            fields=fields, 
                                            order=order)
            if version:
                # got a version
                rv_context = version

        if rv_context is None and self.context.entity:
            # fall back on entity
            # try to extract a version (because versions are launched in a really nice way
            # in Screening Room, while entities are not so nice...)
            self.log_debug("Looking for versions connected to %s..." % self.context.entity)
            filters = [["entity", "is", self.context.entity]]
            order   = [{"field_name": "created_at", "direction": "desc"}]
            fields  = ["id"]
            version = self.shotgun.find_one("Version", 
                                            filters=filters, 
                                            fields=fields, 
                                            order=order)
            
            if version:
                # got a version
                rv_context = version
            else:
                # no versions, fall back onto just the entity
                rv_context = self.context.entity
        
        if rv_context is None:
            # fall back on project
            rv_context = self.context.project
            
        if rv_context is None:
            raise TankError("Not able to figure out a current context to launch screening room for!")
        
        self.log_debug("Closest match to current context is %s" % rv_context)
        
        return rv_context
        
        
    def _start_screeningroom_web(self):
        """
        Launches the screening room web player
        """
        from tank.platform.qt import QtGui, QtCore
        
        entity = self._get_entity()

        # url format is 
        # https://playbook.shotgunstudio.com/page/screening_room?entity_type=Version&entity_id=222
        url = "%s/page/screening_room?entity_type=%s&entity_id=%s" % (self.shotgun.base_url, 
                                                                      entity.get("type"),
                                                                      entity.get("id"))
        
        self.log_debug("Opening url %s" % url)
        
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
        
        
    def _start_screeningroom_rv(self):
        """
        Launches the screening room rv player
        """
        entity = self._get_entity()
        tk_multi_screeningroom = self.import_module("tk_multi_screeningroom")
        
        try:
            rv_path = self._get_rv_binary()
            self.execute_hook_method("init_hook", "before_rv_launch", path=rv_path)
            tk_multi_screeningroom.screeningroom.launch_timeline(base_url=self.shotgun.base_url,
                                                    context=entity,
                                                    path_to_rv=rv_path)
        except Exception, e:
            self.log_error("Could not launch RV Screening Room. Error reported: %s" % e)
    
