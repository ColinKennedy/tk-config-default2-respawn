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
"""
import sgtk
import os
from sgtk.platform.qt import QtCore

class Submitter(object):
    
    def __init__(self):
        """
        Construction
        """
        self.__app = sgtk.platform.current_bundle()
    
    def submit_version(self, path_to_frames, path_to_movie, thumbnail_path, sg_publishes,
                        sg_task, comment, store_on_disk, first_frame, last_frame, 
                        upload_to_shotgun):
        """
        Create a version in Shotgun for this path and linked to this publish.
        """
        
        # get current shotgun user
        current_user = sgtk.util.get_current_user(self.__app.sgtk)
        
        # create a name for the version based on the file name
        # grab the file name, strip off extension
        name = os.path.splitext(os.path.basename(path_to_movie))[0]
        # do some replacements
        name = name.replace("_", " ")
        # and capitalize
        name = name.capitalize()
        
        # Create the version in Shotgun
        ctx = self.__app.context
        data = {
            "code": name,
            "sg_status_list": self.__app.get_setting("new_version_status"),
            "entity": ctx.entity,
            "sg_task": sg_task,
            "sg_first_frame": first_frame,
            "sg_last_frame": last_frame,
            "frame_count": (last_frame-first_frame+1),
            "frame_range": "%s-%s" % (first_frame, last_frame),
            "sg_frames_have_slate": False,
            "created_by": current_user,
            "user": current_user,
            "description": comment,
            "sg_path_to_frames": path_to_frames,
            "sg_movie_has_slate": True,
            "project": ctx.project,
        }

        if sgtk.util.get_published_file_entity_type(self.__app.sgtk) == "PublishedFile":
            data["published_files"] = sg_publishes
        else:# == "TankPublishedFile"
            if len(sg_publishes) > 0:
                if len(sg_publishes) > 1:
                    self.__app.log_warning("Only the first publish of %d can be registered for the new version!" % len(sg_publishes))
                data["tank_published_file"] = sg_publishes[0]

        if store_on_disk:
            data["sg_path_to_movie"] = path_to_movie

        sg_version = self.__app.sgtk.shotgun.create("Version", data)
        self.__app.log_debug("Created version in shotgun: %s" % str(data))
        
        # upload files:
        self._upload_files(sg_version, path_to_movie, thumbnail_path, upload_to_shotgun)
        
        return sg_version
    
    def _upload_files(self, sg_version, output_path, thumbnail_path, upload_to_shotgun):
        """
        """
        # Upload in a new thread and make our own event loop to wait for the
        # thread to finish.
        event_loop = QtCore.QEventLoop()
        thread = UploaderThread(self.__app, sg_version, output_path, thumbnail_path, upload_to_shotgun)
        thread.finished.connect(event_loop.quit)
        thread.start()
        event_loop.exec_()
        
        # log any errors generated in the thread
        for e in thread.get_errors():
            self.__app.log_error(e)
        
    

class UploaderThread(QtCore.QThread):
    """
    Simple worker thread that encapsulates uploading to shotgun.
    Broken out of the main loop so that the UI can remain responsive
    even though an upload is happening
    """
    def __init__(self, app, version, path_to_movie, thumbnail_path, upload_to_shotgun):
        QtCore.QThread.__init__(self)
        self._app = app
        self._version = version
        self._path_to_movie = path_to_movie
        self._thumbnail_path = thumbnail_path
        self._upload_to_shotgun = upload_to_shotgun
        self._errors = []

    def get_errors(self):
        """
        can be called after execution to retrieve a list of errors
        """
        return self._errors

    def run(self):
        """
        Thread loop
        """
        upload_error = False

        if self._upload_to_shotgun:
            try:
                self._app.sgtk.shotgun.upload("Version", self._version["id"], self._path_to_movie, "sg_uploaded_movie")
            except Exception, e:
                self._errors.append("Movie upload to Shotgun failed: %s" % e)
                upload_error = True

        if not self._upload_to_shotgun or upload_error:
            try:
                self._app.sgtk.shotgun.upload_thumbnail("Version", self._version["id"], self._thumbnail_path)
            except Exception, e:
                self._errors.append("Thumbnail upload to Shotgun failed: %s" % e)

