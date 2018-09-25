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
import sys
from datetime import datetime 
import tempfile
from itertools import chain

import tank
from tank import TankError
from tank.platform.qt import QtCore, QtGui
from tank_vendor import yaml

from .string_utils import safe_to_string

class Snapshot(object):
    """
    Main snapshot handler
    """
    
    # Format of the timestamp used in snapshot files
    TIMESTAMP_FMT = "%Y-%m-%d-%H-%M-%S"
    
    # cache of user details
    _user_details_cache = {}
    
    def __init__(self, app):
        """
        Construction
        
        Note, this class is shared between multiple commands so should be stateless
        """
        self._app = app
        self._last_snapshot_result = None
        
        self._work_template = self._app.get_template("template_work")
        self._snapshot_template = self._app.get_template("template_snapshot")

    def _do_scene_operation(self, operation, path=None, result_type=None):
        """
        Do the specified scene operation with the specified args
        """
        result = None
        try:
            result = self._app.execute_hook("hook_scene_operation", operation=operation, file_path=path)     
        except TankError, e:
            # deliberately filter out exception that used to be thrown 
            # from the scene operation hook but has since been removed
            if not str(e).startswith("Don't know how to perform scene operation '"):
                # just re-raise the exception:
                raise
            
        # validate the result if needed:
        if result_type and (result == None or not isinstance(result, result_type)):
            raise TankError("Unexpected type returned from 'hook_scene_operation' for operation '%s' - expected '%s' but returned '%s'" 
                            % (operation, result_type.__name__, type(result).__name__))
        
        return result
        
    def save_current_file(self):
        """
        Use hook to save the current work/scene file
        """
        self._app.log_debug("Saving the current file with hook")
        self._do_scene_operation("save")
        
    def get_current_file_path(self):
        """
        Use hook to get the current work/scene file path
        """
        self._app.log_debug("Retrieving current scene path via hook")
        return self._do_scene_operation("current_path", result_type=basestring)

    def open_file(self, file_path):
        """
        Use hook to open the specified file
        """
        self._app.log_debug("Opening file '%s' via hook" % file_path)
        self._do_scene_operation("open", file_path)
        
    def _reset_current_scene(self):
        """
        Use hook to clear the current scene
        """
        self._app.log_debug("Resetting the current scene via hook")
        return self._do_scene_operation("reset") != False
        
    def copy_file(self, source_path, target_path):
        """
        Use hook to copy source file to target path
        """
        self._app.execute_hook("hook_copy_file", source_path=source_path, target_path=target_path)
    
    def can_snapshot(self, work_path=None):
        """
        Returns True if a snapshot can be created with work_path.
        If work_path is None, the current_file_path is used.
        """
        work_path = work_path or self.get_current_file_path()
        if not os.path.exists(work_path):
            return False
        if not self._work_template.validate(work_path):
            return False
        return True

    def do_snapshot(self, work_path, thumbnail, comment):
        """
        Do a snapshot using the specified details
        """
        self._last_snapshot_result = None
        
        # save the current scene:
        self.save_current_file()

        # ensure work file exists:
        if not os.path.exists(work_path):
            raise TankError("Snapshot: Work file %s could not be found on disk!" % work_path)

        # validate work file:
        if not self._work_template.validate(work_path):
            raise TankError("Unable to snapshot non-work file %s" % work_path)

        # use work file to find fields for snapshot:
        fields = self._work_template.get_fields(work_path)
        fields = dict(chain(self._app.context.as_template_fields(self._snapshot_template).iteritems(), fields.iteritems()))

        # add additional fields:
        fields["timestamp"] = datetime.now().strftime(Snapshot.TIMESTAMP_FMT)
        
        if "increment" in self._snapshot_template.keys:
            # work out next increment from existing snapshots:
            fields["increment"] = self._find_next_snapshot_increment(fields)

        # generate snapshot path:
        snapshot_path = self._snapshot_template.apply_fields(fields)

        # copy file via hook:
        self._app.log_debug("Snapshot: Copying %s --> %s" % (work_path, snapshot_path))
        self.copy_file(work_path, snapshot_path)

        # make sure snapshot exists:
        if not os.path.exists(snapshot_path):
            raise TankError("Snapshot: Failed to copy work file from '%s' to '%s'" 
                            % (work_path, snapshot_path))

        # ok, snapshot succeeded so update comment and thumbnail if we have them:
        self._add_snapshot_comment(snapshot_path, comment)
        if thumbnail:
            self._add_snapshot_thumbnail(snapshot_path, thumbnail)

        self._last_snapshot_result = snapshot_path
        return self._last_snapshot_result
        
    def restore_snapshot(self, current_path, snapshot_path, snapshot_current=True):
        """
        Restore snapshot from the specified path
        """
        if not current_path or not snapshot_path:
            return

        # to be on the safe side, save the current file
        # as it may be overidden:
        self.save_current_file()

        if snapshot_current:
            # check to see if work file exists and if it does, snapshot it first:
            if os.path.exists(current_path):
                try:
                    comment = ("Automatic snapshot before restoring older snapshot '%s'" 
                               % os.path.basename(snapshot_path))
                    self.do_snapshot(current_path, None, comment)
                except:
                    # reformat error?
                    raise
        
        # reset the current scene in case the file is locked by being 
        # open - Softimage does this!
        if not self._reset_current_scene():
            raise TankError("Failed to reset the scene!")
        
        # now use hook to copy snapshot back to work path:
        self._app.log_debug("Snapshot Restore: Copying %s --> %s" % (snapshot_path, current_path))
        self.copy_file(snapshot_path, current_path)
        
        # finally, use hook to re-open work file:
        self._app.log_debug("Snapshot Restore: Opening %s" % (current_path))
        self.open_file(current_path)

    def find_snapshot_history(self, file_path):
        """
        Find snapshot history for specified file
        """
        history = []
        if not file_path:
            return history
        
        # get fields using the work template:
        fields = []
        if self._work_template.validate(file_path):
            fields = self._work_template.get_fields(file_path)
        elif self._snapshot_template.validate(file_path):
            fields = self._snapshot_template.get_fields(file_path)
        else:
            # not a valid work file or snapshot!
            return history
        
        # combine with context fields:
        fields = dict(chain(self._app.context.as_template_fields(self._snapshot_template).iteritems(), fields.iteritems()))

        
        # find files that match the snapshot template ignoring certain fields:
        files = self._app.tank.paths_from_template(self._snapshot_template, 
                                             fields, 
                                             ["version", "timestamp", "increment"])
        if len(files) == 0:
            return history 
        
        # load comments & thumbnails and build history:
        comments = self._get_snapshot_comments(files[0])
        
        for file in files:
            # extract any details we have from the comments:
            comment_details = comments.get(os.path.basename(file), {})
            comment = comment_details.get("comment", "")
            sg_user = comment_details.get("sg_user")
            details = {"file":file, 
                       "comment":comment, 
                       "thumbnail_path":self._get_thumbnail_file_path(file)
                       }
            
            # add additional details if we have then:
            fields = self._snapshot_template.get_fields(file)
            
            for key_name in ["version", "increment"]:
                if key_name in fields.keys():
                    details[key_name] = fields[key_name]

            timestamp = fields.get("timestamp")
            if timestamp:
                details["datetime"] = datetime.strptime(timestamp, Snapshot.TIMESTAMP_FMT)
                 
            # user
            if sg_user:
                details["user"] = sg_user
            else:
                # try to get the user that last modified the file:
                details["user"] = self._get_file_last_modified_user(file)
            
            history.append(details)
            
        return history 

    def get_history_display_name(self, path):
        """
        Get a nice display name for the snapshot history list
        """
        return self._get_file_display_name(path, self._work_template) or "Unknown"

    def _get_file_display_name(self, path, template, fields=None):
        """
        Return the 'name' to be used for the file - if possible
        this will return a 'versionless' name
        """
        # first, extract the fields from the path using the template:
        if fields:
            fields = fields.copy()
        else:
            try:
                fields = template.get_fields(path)
            except TankError:
                # template not valid for path!
                return None

        if "name" in fields and fields["name"]:
            # well, that was easy!
            name = fields["name"]
        else:
            # find out if version is used in the file name:
            template_name, _ = os.path.splitext(os.path.basename(template.definition))
            version_in_name = "{version}" in template_name
        
            # extract the file name from the path:
            name, _ = os.path.splitext(os.path.basename(path))
            delims_str = "_-. "
            if version_in_name:
                # looks like version is part of the file name so we        
                # need to isolate it so that we can remove it safely.  
                # First, find a dummy version whose string representation
                # doesn't exist in the name string
                version_key = template.keys["version"]
                dummy_version = 9876
                while True:
                    test_str = version_key.str_from_value(dummy_version)
                    if test_str not in name:
                        break
                    dummy_version += 1
                
                # now use this dummy version and rebuild the path
                fields["version"] = dummy_version
                path = template.apply_fields(fields)
                name, _ = os.path.splitext(os.path.basename(path))
                
                # we can now locate the version in the name and remove it
                dummy_version_str = version_key.str_from_value(dummy_version)
                
                v_pos = name.find(dummy_version_str)
                # remove any preceeding 'v'
                pre_v_str = name[:v_pos].rstrip("v")
                post_v_str = name[v_pos + len(dummy_version_str):]
                
                if (pre_v_str and post_v_str 
                    and pre_v_str[-1] in delims_str 
                    and post_v_str[0] in delims_str):
                    # only want one delimiter - strip the second one:
                    post_v_str = post_v_str.lstrip(delims_str)

                versionless_name = pre_v_str + post_v_str
                versionless_name = versionless_name.strip(delims_str)
                
                if versionless_name:
                    # great - lets use this!
                    name = versionless_name
                else: 
                    # likely that version is only thing in the name so 
                    # instead, replace the dummy version with #'s:
                    zero_version_str = version_key.str_from_value(0)        
                    new_version_str = "#" * len(zero_version_str)
                    name = name.replace(dummy_version_str, new_version_str)
        
        return name  

    def _get_file_last_modified_user(self, path):
        """
        Get the user details of the last person
        to modify the specified file        
        """
        login_name = None
        if sys.platform == "win32":
            # TODO: add windows support..
            pass
        else:
            try:
                from pwd import getpwuid                
                login_name = getpwuid(os.stat(path).st_uid).pw_name
            except:
                pass
        
        if login_name:
            return self._get_user_details(login_name)
        
        return None

    def _get_user_details(self, login_name):
        """
        Get the shotgun HumanUser entry:
        """
        sg_user = Snapshot._user_details_cache.get(login_name)
        if not sg_user:
            try:
                filter = ["login", "is", login_name]
                fields = ["id", "type", "email", "login", "name", "image"]
                sg_user = self._app.shotgun.find_one("HumanUser", [filter], fields)
            except:
                pass
            Snapshot._user_details_cache[login_name] = sg_user
        return sg_user

    def show_snapshot_dlg(self):
        """
        Perform a snapshot of the current work file with the help of the UI
        """
      
        # get current work file path:
        try:
            work_file_path = self.get_current_file_path()
        except Exception, e:
            msg = ("Failed to get the current file path:\n\n"
                  "%s\n\n"
                  "Unable to continue!" % e)
            QtGui.QMessageBox.critical(None, "Snapshot Error!", msg)
            return False
        
        # current scene path must match work template and contain version:
        if not work_file_path or not self._work_template.validate(work_file_path):
            msg = ("Unable to snapshot!\n\nPlease save the scene as a valid work file before continuing")
            QtGui.QMessageBox.information(None, "Unable To Snapshot!", msg)

            # try to launch "Shotgun Save As" command if we have it:            
            save_as_cmd = tank.platform.current_engine().commands.get("Shotgun Save As...")
            if not save_as_cmd:
                # try old name, just in case
                save_as_cmd = tank.platform.current_engine().commands.get("Tank Save As...")
            if save_as_cmd:
                save_as_cmd["callback"]()

            return False
        
        # get initial thumbnail if there is one:
        thumbnail = QtGui.QPixmap(self._app.execute_hook("hook_thumbnail"))
        
        # show snapshot dialog as modal dialog:
        self._last_snapshot_result = None
        
        from .snapshot_form import SnapshotForm
        (res, snapshot_widget) = self._app.engine.show_modal("Snapshot", self._app, SnapshotForm, work_file_path, thumbnail, self._setup_snapshot_ui)
        
        snapshot_success = (self._last_snapshot_result != None)
        
        # special case return code to show history dialog:
        if res == SnapshotForm.SHOW_HISTORY_RETURN_CODE:
            # snapshot history dialog is modeless so this won't block!
            self.show_snapshot_history_dlg()

        # disconnect from the widget to allow the widget to be cleaned up:
        snapshot_widget.snapshot.disconnect(self._do_snapshot_from_ui)

        # return if snapshot was actually done
        return snapshot_success
        
    def _setup_snapshot_ui(self, snapshot_widget):
        """
        Called during snapshot dialog creation to give us a
        chance to hook up signals etc.
        """
        snapshot_widget.snapshot.connect(self._do_snapshot_from_ui)
        
    def _do_snapshot_from_ui(self, snapshot_widget, file_path):
        """
        Triggered when user clicks 'Create Snapshot' button
        in the UI
        """
        # get data from widget:
        thumbnail = snapshot_widget.thumbnail
        comment = snapshot_widget.comment

        file_path = safe_to_string(file_path)

        # try to do the snapshot
        status = True
        msg = ""
        try:
            self.do_snapshot(file_path, thumbnail, comment)
        except Exception, e:
            status = False
            msg = "%s" % e
            
        # update UI:
        snapshot_widget.show_result(status, msg)

    def show_snapshot_history_dlg(self):
        """
        Show the snapshot history UI for the current path
        """
        
        # create dialog:
        from .snapshot_history_form import SnapshotHistoryForm
        snapshot_history_form = self._app.engine.show_dialog("Snapshot History", self._app, SnapshotHistoryForm, self._app, self)
        
        # hook up signals:
        snapshot_history_form.restore.connect(self._on_history_restore_snapshot)
        snapshot_history_form.snapshot.connect(self._on_history_do_snapshot)
        snapshot_history_form.closed.connect(self._on_history_dlg_closed)
 
    def _on_history_dlg_closed(self, widget):
        """
        Called when the history dialog is closed.  Hooks are 
        disconnected to allow the widget to be released
        """
        widget.restore.disconnect(self._on_history_restore_snapshot)
        widget.snapshot.disconnect(self._on_history_do_snapshot)
        widget.closed.disconnect(self._on_history_dlg_closed)

    def _on_history_restore_snapshot(self, snapshot_history_form, current_path, snapshot_path):
        """
        Restore the specified snapshot
        """
        # double check that the current path is still correct - if 
        # it's not then something happened to change the current scene
        # this can happen because this isn't a modal dialog!

        current_path = safe_to_string(current_path)
        snapshot_path = safe_to_string(snapshot_path)

        actual_current_path = self.get_current_file_path()
        if actual_current_path != current_path:
            snapshot_history_form.refresh()
            return
        
        # confirm snapshot restore:
        res = QtGui.QMessageBox.question(None,  "Restore Snapshot?", 
                                         "Do you want to snapshot the current work file before restoring?", 
                                         QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.Cancel)
        if res == QtGui.QMessageBox.Cancel:
            return

        # do snapshot restore
        snapshot_current = (res == QtGui.QMessageBox.Yes)
        try:
            self.restore_snapshot(current_path, snapshot_path, snapshot_current=snapshot_current)
        except TankError, e:
            QtGui.QMessageBox.critical(None, "Snapshot Restore Failed!", e)
            return
        except Exception, e:
            self._app.log_exception("Snapshot Restore Failed!")
            return
        
        snapshot_history_form.close()
        
    def _on_history_do_snapshot(self, snapshot_history_form):
        """
        Switch to the snapshot UI from the history UI
        """
        # close the snapshot history window
        snapshot_history_form.close()
            
        # do a snapshot:
        self.show_snapshot_dlg()
   
    def _find_next_snapshot_increment(self, snapshot_fields):
        # Get list of existing snapshot paths
        files = self._app.tank.paths_from_template(self._snapshot_template, 
                                                   snapshot_fields, 
                                                   ["timestamp", "increment"])

        # Get maximum existing snapshot increment, defaulting to 0.
        increment = 0
        for f in files:
            file_increment = self._snapshot_template.get_fields(f).get("increment", 0)
            increment = max(file_increment, increment)

        return increment + 1
        
    def _add_snapshot_thumbnail(self, snapshot_file_path, thumbnail):
        """
        Save a thumbnail for the specified snapshot file path
        """
        if not thumbnail or thumbnail.isNull():
            return

        # write out to tmp path:
        temp_file, temp_path = tempfile.mkstemp(suffix=".png", prefix="tanktmp")
        if temp_file:
            os.close(temp_file)

        try:
            if not thumbnail.save(temp_path, "PNG"):
                raise TankError("Snapshot: Failed to save thumbnail to '%s'" % temp_path)
            
            # work out actual path:
            thumbnail_path = self._get_thumbnail_file_path(snapshot_file_path)
            
            # finally, use hook to copy:
            self._app.log_debug("Snapshot: Copying %s --> %s" % (temp_path, thumbnail_path))
            self.copy_file(temp_path, thumbnail_path)
        finally:
            os.remove(temp_path)

    def _get_thumbnail_file_path(self, snapshot_file_path):
        """
        Return path to snapshot thumbnail.  File path will be:

            <snapshot_dir>/<work_file_v0_name>.tank_thumb.png
            
        """
        thumbnail_path = "%s.tank_thumb.png" % os.path.splitext(snapshot_file_path)[0]
        return thumbnail_path
        
    def _get_comments_file_path(self, snapshot_file_path):
        """
        Snapshot comments file path will be:
        
            <snapshot_dir>/<work_file_v0_name>_comments.yml
            
        The assumption is that the snapshot template contains all fields
        required to reconstruct the work file - this has to be the case 
        though as otherwise we would never be able to restore a snapshot!
        """
        snapshot_dir = os.path.dirname(snapshot_file_path)
        fields = self._snapshot_template.get_fields(snapshot_file_path)
        
        # combine with context fields:
        fields = dict(chain(self._app.context.as_template_fields(self._work_template).iteritems(), fields.iteritems()))
        
        # always save with version = 0 so that comments for all
        # versions are saved in the same file.
        fields["version"] = 0 
        
        work_path = self._work_template.apply_fields(fields)
        work_file_name = os.path.basename(work_path)
        work_file_title = os.path.splitext(work_file_name)[0]
        comments_file_path = "%s/%s.tank_comments.yml" % (snapshot_dir, work_file_title)
        
        return comments_file_path

        
    def _load_nuke_publish_snapshot_comments(self, snapshot_file_path):
        """
        Load old nuke-style snapshot comments if they exist.  These are only
        ever read - all new comments are saved to the new file.
        """
        comments = {}
        try:
            # look for old nuke style path:        
            snapshot_dir = os.path.dirname(snapshot_file_path)
            fields = self._snapshot_template.get_fields(snapshot_file_path)
            
            SNAPSHOT_COMMENTS_FILE = r"%s_comments.yml"
            comments_file_name = SNAPSHOT_COMMENTS_FILE % fields.get("name", "unknown")
            comments_file_path = os.path.join(snapshot_dir, comments_file_name)
            
            comments = {}
            if os.path.exists(comments_file_path):
                raw_comments = yaml.load(open(comments_file_path, "r"))
                for (name, timestamp), comment in raw_comments.iteritems():
                    fields["name"] = name
                    fields["timestamp"] = timestamp
                    snapshot_path = self._snapshot_template.apply_fields(fields)
                    
                    if os.path.exists(snapshot_path):
                        # add comment to dictionary in new style:
                        comments_key = os.path.basename(snapshot_path)
                        comments[comments_key] = {"comment":comment}
        except:
            # it's not critical that this succeeds so just ignore any exceptions
            pass
            
        return comments
        
    def _add_snapshot_comment(self, snapshot_file_path, comment):
        """
        Add a comment to the comment file for a snapshot file.  The comments are stored
        in the following format:
        
        {<snapshot file name> : {
            comment:    String - comment to store
            sg_user:    Shotgun entity dictionary representing the user that created the snapshot
            }
         ...
        }

        :param str file_path: path to the snapshot file.
        :param str comment: comment string to save.

        """
        # validate to make sure path is sane
        if not self._snapshot_template.validate(snapshot_file_path):
            self._app.log_warning("Could not add comment to "
                                         "invalid snapshot path %s!" % snapshot_file_path)
            return

        # get comments file path:        
        comments_file_path = self._get_comments_file_path(snapshot_file_path)
        self._app.log_debug("Snapshot: Adding comment to file %s" % comments_file_path)
        
        # load yml file
        comments = {}
        if os.path.exists(comments_file_path):
            comments = yaml.load(open(comments_file_path, "r"))

        # comment is now a dictionary so that we can also include the user:
        comments_value = {"comment":comment, "sg_user":self._app.context.user}
            
        # add entry for snapshot file:
        comments_key = os.path.basename(snapshot_file_path)
        comments[comments_key] = comments_value
        
        # and save yml file
        old_umask = os.umask(0) 
        try:
            yaml.dump(comments, open(comments_file_path, "w"))
        finally:
            os.umask(old_umask) 
        
    
    def _get_snapshot_comments(self, snapshot_file_path):
        """
        Return the snapshot comments for the specified file path
        """
        # first, attempt to load old-nuke-publish-style comments:
        comments = self._load_nuke_publish_snapshot_comments(snapshot_file_path)
        
        # now load new style comments:
        comments_file_path = self._get_comments_file_path(snapshot_file_path)
        raw_comments = {}
        if os.path.exists(comments_file_path):
            raw_comments = yaml.load(open(comments_file_path, "r"))
            
        # process raw comments to convert old-style to new if need to:
        for key, value in raw_comments.iteritems():
            if isinstance(value, basestring):
                # old style string
                comments[key] = {"comment":value}
            elif isinstance(value, dict):
                # new style dictionary
                comments[key] = value
            else:
                # value isn't valid!
                pass
                
        # ensure all comments are returned as utf-8 strings rather than
        # unicode - this is due to a previous bug where the snapshot UI
        # would return the comment as unicode!
        for comment_dict in comments.values():
            comment = comment_dict.get("comment")
            if comment and isinstance(comment, unicode):
                comment_dict["comment"] = comment.encode("utf8")
            
        return comments        
