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
Menu handling for Nuke

"""
import os
import sys
import webbrowser
import unicodedata

from pyfbsdk import FBSystem
from pyfbsdk import FBMenuManager 
from pyfbsdk import FBGenericMenu

class MenuGenerator(object):
    """
    Menu generation functionality for Nuke
    """

    def __init__(self, engine, menu_name):
        self._engine = engine
        self._menu_name = menu_name
        self.__menu_index = 1
        self._callbacks = {}
        
        # Currently, root-level menu items seem to cause Motionbuilder 2011 & 2012 to 
        # crash (2013+ works fine though).  sub-menus work correctly so for <=2012 we 
        # force everything to be at least one level deep so at least it's stable!        
        fb_sys = FBSystem()
        self.__all_menus_nested = (fb_sys.Version < 13000.0)  

    ##########################################################################################
    # public methods
    
    def create_menu(self):
        """
        Render the entire Shotgun menu.
        """
        # create main menu
        menu_mgr = FBMenuManager()
        sg_menu = menu_mgr.GetMenu(self._menu_name)
        if not sg_menu:
            menu_mgr.InsertBefore(None, "&Help", self._menu_name)
            sg_menu = menu_mgr.GetMenu(self._menu_name)
            
        if not self.__all_menus_nested:
            # need to handle root-level menu items
            sg_menu.OnMenuActivate.Add(self.__menu_event)
        
        # now add the context item on top of the main menu
        context_menu = self._add_context_menu(sg_menu)

        # add separator:
        sg_menu.InsertLast("", self.__next_menu_index())

        # now add favourites
        favourites_menu = None
        for fav in self._engine.get_setting("menu_favourites"):
            app_instance_name = fav["app_instance"]
            menu_name = fav["name"]

            # scan through all menu items
            for (cmd_name, cmd_details) in self._engine.commands.items():
                cmd = AppCommand(cmd_name, cmd_details)
                if cmd.get_app_instance_name() == app_instance_name and cmd.name == menu_name:
                    # found our match!                    
                    if self.__all_menus_nested:
                        # workaround for bug in 2012 which causes Motionbuilder to crash
                        # when clicking on root-level menu items
                        if not favourites_menu:
                            favourites_menu = FBGenericMenu()
                            favourites_menu.OnMenuActivate.Add(self.__menu_event)
                            sg_menu.InsertLast("Favorites", self.__next_menu_index(), favourites_menu)                            
                    else:
                        favourites_menu = sg_menu
                    
                    # add to the favourites section of the menu:
                    cmd.add_command_to_menu(favourites_menu, self.__next_menu_index())
                    
                    # mark as a favourite item
                    cmd.favourite = True            

        if favourites_menu:
            # add separator:
            sg_menu.InsertLast("", self.__next_menu_index())

        # now go through all of the menu items.
        # separate them out into various sections
        commands_by_app = {}

        for (cmd_name, cmd_details) in self._engine.commands.items():
            cmd = AppCommand(cmd_name, cmd_details)

            if cmd.get_type() == "context_menu":
                # context menu!
                cmd.add_command_to_menu(context_menu, self.__next_menu_index())
                self._add_event_callback(cmd.name, cmd.callback)
            else:
                # normal menu
                app_name = cmd.get_app_name()
                if app_name is None:
                    # un-parented app
                    app_name = "Other Items"
                if not app_name in commands_by_app:
                    commands_by_app[app_name] = []
                commands_by_app[app_name].append(cmd)

        # now add all apps to main menu
        self._add_app_menu(sg_menu, commands_by_app)

    def destroy_menu(self):
        menu_mgr = FBMenuManager()
        menu = menu_mgr.GetMenu(self._menu_name)
        
        if menu:
            item = menu.GetFirstItem()
            while item:
                next_item = menu.GetNextItem(item)
                menu.DeleteItem(item)
                item = next_item
            self.__menu_index = 1
            self._callbacks = {}

    ##########################################################################################
    # context menu and UI

    def _add_context_menu(self, menu):
        """
        Adds a context menu which displays the current context
        """

        ctx = self._engine.context
        ctx_name = str(ctx)

        # create the menu object
        ctx_menu = FBGenericMenu()

        ctx_menu.InsertLast("Jump to Shotgun", self.__next_menu_index())
        self._add_event_callback("Jump to Shotgun", self._jump_to_sg)

        ctx_menu.InsertLast("Jump to File System", self.__next_menu_index())
        self._add_event_callback("Jump to File System", self._jump_to_fs)

        ctx_menu.OnMenuActivate.Add(self.__menu_event)

        menu.InsertFirst(ctx_name, self.__next_menu_index(), ctx_menu)
        return ctx_menu

    def _add_event_callback(self, event_name, callback):
        """
        Creates a mapping between the menu item name and the callback that should be
        run when it is clicked.
        """
        self._callbacks[event_name] = callback

    def _jump_to_sg(self):
        """
        Jump to shotgun, launch web browser
        """        
        url = self._engine.context.shotgun_url        
        webbrowser.open(url)

    def _jump_to_fs(self):
        """
        Jump from context to FS
        """
        # launch one window for each location on disk
        paths = self._engine.context.filesystem_locations
        for disk_location in paths:

            # get the setting        
            system = sys.platform
            
            # run the app
            if system == "linux2":
                cmd = 'xdg-open "%s"' % disk_location
            elif system == "darwin":
                cmd = 'open "%s"' % disk_location
            elif system == "win32":
                cmd = 'cmd.exe /C start "Folder" "%s"' % disk_location
            else:
                raise Exception("Platform '%s' is not supported." % system)

            exit_code = os.system(cmd)
            if exit_code != 0:
                self._engine.log_error("Failed to launch '%s'!" % cmd)

    ##########################################################################################
    # app menus

    def _add_app_menu(self, menu, commands_by_app):
        """
        Add all apps to the main menu, process them one by one.
        """

        for i, app_name in enumerate(sorted(commands_by_app.keys())):
            if self.__all_menus_nested or len(commands_by_app[app_name]) > 1:
                # more than one menu entry for this app
                # make a sub menu and put all items in the sub menu
                app_menu = FBGenericMenu()
                for j, cmd in enumerate(commands_by_app[app_name]):
                    cmd.add_command_to_menu(app_menu, self.__next_menu_index())
                    self._add_event_callback(cmd.name, cmd.callback)
                app_menu.OnMenuActivate.Add(self.__menu_event)
                app_name = self.__strip_unicode(app_name)
                menu.InsertLast(app_name, self.__next_menu_index(), app_menu)
            else:
                # this app only has a single entry.
                # display that on the menu
                # todo: Should this be labelled with the name of the app
                # or the name of the menu item? Not sure.
                cmd_obj = commands_by_app[app_name][0]
                if not cmd_obj.favourite:
                    cmd_obj.add_command_to_menu(menu, self.__next_menu_index())
                    self._add_event_callback(cmd_obj.name, cmd_obj.callback)

    ##########################################################################################
    # private methods

    def __next_menu_index(self):
        """
        Get the next sequential menu index.  I think these need to be 
        unique within the Shotgun menu but they aren't used directly 
        by Toolkit anywhere
        """
        idx = self.__menu_index
        self.__menu_index += 1
        return idx

    def __menu_event(self, control, event):
        """
        Handles menu events.
        """
        callback = self._callbacks.get(event.Name)
        if callback:
            # execute callback through a Qt singleShot timer event
            # to disconnect the command from the menu.  Otherwise
            # any apps that restart the engine (causing the menu to
            # be rebuilt) can cause Motionbuilder to crash!
            from sgtk.platform.qt import QtCore
            QtCore.QTimer.singleShot(100, callback)
            
    def __strip_unicode(self, val):
        """
        Get rid of unicode
        """
        if val.__class__ == unicode:
            val = unicodedata.normalize('NFKD', val).encode('ascii', 'ignore')
        return val   
            

class AppCommand(object):
    """
    Wraps around a single command that you get from engine.commands
    """

    def __init__(self, name, command_dict):

        self.properties = command_dict["properties"]
        self.callback = command_dict["callback"]
        self.favourite = False
        
        # deal with mobu's inability to handle unicode. #fail
        if name.__class__ == unicode:
            self.name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore')
        else:
            self.name = name

    def get_app_name(self):
        """
        Returns the name of the app that this command belongs to
        """
        if "app" in self.properties:
            return self.properties["app"].display_name
        return None

    def get_app_instance_name(self):
        """
        Returns the name of the app instance, as defined in the environment.
        Returns None if not found.
        """
        if "app" not in self.properties:
            return None

        app_instance = self.properties["app"]
        engine = app_instance.engine

        for (app_instance_name, app_instance_obj) in engine.apps.items():
            if app_instance_obj == app_instance:
                # found our app!
                return app_instance_name

        return None

    def get_documentation_url_str(self):
        """
        Returns the documentation as a str
        """
        if "app" in self.properties:
            app = self.properties["app"]
            doc_url = app.documentation_url
            # deal with nuke's inability to handle unicode. #fail
            if doc_url.__class__ == unicode:
                doc_url = unicodedata.normalize('NFKD', doc_url).encode('ascii', 'ignore')
            return doc_url

        return None

    def get_type(self):
        """
        returns the command type. Returns node, custom_pane or default
        """
        return self.properties.get("type", "default")

    def add_command_to_menu(self, menu, index):
        """
        Adds an app command to the menu
        """
        # std shotgun menu
        menu.InsertLast(self.name, index)
