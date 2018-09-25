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
A simple list view showing the publishes selected for the new project creation
"""

import os
from datetime import datetime, timedelta

import sgtk
from sgtk.platform.qt import QtCore, QtGui

browser_widget = sgtk.platform.import_framework("tk-framework-widget", "browser_widget")

class PublishListView(browser_widget.BrowserWidget):
    """
    UI for displaying a list of snapshot items
    """
    
    # signal emitted when the user is requesting that publishes be removed from the list
    remove_publishes = QtCore.Signal(list)
    
    def __init__(self, parent=None):
        """
        Construction
        
        :param parent:    The parent QWidget
        """
        browser_widget.BrowserWidget.__init__(self, parent)
        
        # tweak style
        self.title_style = "none"
        self.enable_search(False)
        self.enable_multi_select(True)
        self.set_label("")
        self.ui.browser_header.setVisible(False)
        
        # cache of publish images that we've looked up from Shotgun.  Used to
        # avoid unnecessary lookups.
        self.__publish_images = {}
        
        # add right-click menu to remove items:
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        remove_action = QtGui.QAction("Remove Selected Publishes", self)
        self.addAction(remove_action)
        remove_action.triggered[()].connect(self._on_remove_selected_publishes)
    
    def keyPressEvent(self, event):
        """
        Executed when a key is pressed by the user whilst the list view has focus
        
        :param event:    The key press event details
        """        
        if event.key() in [QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace]:
            self._on_remove_selected_publishes()
        else:
            # call the base class implementation:
            browser_widget.BrowserWidget.keyPressEvent(self, event)
        
    def _on_remove_selected_publishes(self):
        """
        Called when something has requested that selected publishes be removed
        from the list.
        """
        publish_ids = []
        for list_item in self.get_selected_items():
            publish_ids.append(list_item.publish_id)
        if publish_ids:
            self.remove_publishes.emit(publish_ids)
        
    def get_data(self, data):
        """
        Threaded - retrieve the data that will be used to populate the
        list view
        
        :param data:    Information that can be used to retrieve the data
        """
        if data:
            # re-retrieve the thumbnails for the publishes if as the one linked
            # from the publish data might have expired!
            publishes = dict([(p["id"], p) for p in data])
            
            # build a list of publish ids that we need to fetch details for:
            ids_to_fetch = []
            for id, publish in publishes.iteritems():
                if id in self.__publish_images:
                    if self.__publish_images[id]:
                        publish["image"] = self.__publish_images[id]
                else:
                    ids_to_fetch.append(id)
            
            if ids_to_fetch:
                # query Shotgun for the publish details:
                pf_type = data[0]["type"]
                filters = [["id", "in", ids_to_fetch]]
                fields = ["image"]
                try:
                    sg_res = self._app.shotgun.find(pf_type, filters, fields)
                    # update publishes:
                    for id, image in [(r["id"], r.get("image")) for r in sg_res]:
                        self.__publish_images[id] = image
                        if not image:
                            continue
                        publishes[id]["image"] = image
                except:
                    pass
        
        return data
    
    def process_result(self, result):
        """
        Process worker result on main thread - can create list items here.
        
        :param result:    The result passed through from the get_data method
        """
        for sg_publish in result:
            list_item = self.add_item(browser_widget.ListItem)
            list_item.publish_id = sg_publish["id"]
            
            thumbnail_path = sg_publish.get("image")
            name = sg_publish.get("name")
            version = sg_publish.get("version_number")
            entity_type = sg_publish.get("entity", {}).get("type")
            entity_name = sg_publish.get("entity", {}).get("name")
            task_name = sg_publish.get("task.Task.content")
            
            if thumbnail_path:
                list_item.set_thumbnail(thumbnail_path)
            
            line_1 = "<b>%s v%03d</b>" % (name, version)
            line_2 = "%s %s, %s" % (entity_type, entity_name, task_name)
            list_item.set_details("<br>".join([line_1, line_2]))
