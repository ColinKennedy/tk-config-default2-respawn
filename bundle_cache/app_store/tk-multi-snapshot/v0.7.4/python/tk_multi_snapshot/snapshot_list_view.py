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
from datetime import datetime, timedelta

import tank
from tank.platform.qt import QtCore, QtGui

browser_widget = tank.platform.import_framework("tk-framework-widget", "browser_widget")
from .snapshot_item import SnapshotItem

class SnapshotListView(browser_widget.BrowserWidget):
    """
    UI for displaying a list of snapshot items
    """
    
    def __init__(self, parent=None):
        """
        Construction
        """
        browser_widget.BrowserWidget.__init__(self, parent)
        
        # tweak style
        self.title_style = "none"
        
    def get_selected_path(self):
        """
        Get the path of the selected item
        """
        widget = self.get_selected_item()
        if isinstance(widget, SnapshotItem):
            return widget.path
        return ""
    
    def get_data(self, data):
        """
        Get the data needed to populate the list - this
        is done on a worker thread
        """
        handler = data.get("handler")
        if not handler:
            raise TankError("Failed to find valid handler!")
        file_path = data.get("file_path")

        # get snapshot details:
        snapshot_details = handler.find_snapshot_history(file_path)

        # group details by date
        details_by_date = {}
        for details in snapshot_details:
            date = details.get("datetime")
            if date:
                date = date.date()
            details_by_date.setdefault(date, list()).append(details)
            
        # and sort by (datetime, increment) within each day:
        from operator import attrgetter
        for items in details_by_date.values():
            items.sort(key=lambda d:(d.get("datetime"), d.get("increment")), reverse=True)
        
        return details_by_date
    
    def process_result(self, result):
        """
        Process worker result on main thread - can create list items here.
        """
        if len(result) == 0:
            # just show message instead
            self.set_message("Looks like you haven't created any snapshots yet! Click the New Snapshot button to get started.")
            return

        # want to create groups of items in reverse date order
        dates = result.keys()
        dates.sort(reverse=True)
        
        for date in dates:
            items = result[date]
            if not items:
                continue
            
            if date:
                # add header:
                header = self.add_item(browser_widget.ListHeader)
                
                date_str = ""
                time_diff = datetime.now().date() - date
                if time_diff < timedelta(days=1):
                    date_str = "Today"
                elif time_diff < timedelta(days=2):
                    date_str = "Yesterday"
                else:
                    date_str = "%d%s %s" % (date.day, 
                                            self._day_suffix(date.day), 
                                            date.strftime("%B %Y"))
                
                header.set_title("Snapshots From %s" % date_str)
            
            for details in items:
                list_item = self.add_item(SnapshotItem)
                list_item.path = details.get("file")
                                
                # set thumbnail if there is one:
                thumbnail_path = details.get("thumbnail_path")
                if os.path.exists(thumbnail_path):
                    list_item.set_thumbnail(thumbnail_path)
                    
                # build and set details text:
                lines = []
                line = "Version v%03d" % details["version"]
                increment = details.get("increment")
                if increment:
                    line += "/%03d" % increment
                date = details.get("datetime")
                if date:
                    tm = date.time()
                    line += " at %s" % tm.strftime("%H:%M")
                lines.append("<b>%s</b>" % line)
                
                user = details.get("user")
                username = user.get("name") if user else None
                if username:
                    lines.append("Created by %s" % username)
                
                comment = details.get("comment")
                if comment:
                    lines.append("Description: %s" % comment)
                else:
                    lines.append("<i>No description was entered for this snapshot</i>")
                    
                list_item.set_details("<br>".join(lines))

    def _day_suffix(self, day):
        """
        Return the suffix for the day of the month
        """
        return ["th", "st", "nd", "rd"][day%10 if not 11<=day<=13 and day%10 < 4 else 0]
