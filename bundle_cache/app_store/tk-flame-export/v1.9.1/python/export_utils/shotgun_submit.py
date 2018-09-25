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
import pprint
import subprocess
import uuid
from sgtk import TankError
import os
import re

from .util import subprocess_check_output, SubprocessCalledProcessError


class ShotgunSubmitter(object):
    """
    Helper class with methods to submit publishes and versions to Shotgun
    """
    
    # constants
    
    # default height for Shotgun uploads
    # see https://support.shotgunsoftware.com/entries/26303513-Transcoding
    SHOTGUN_QUICKTIME_TARGET_HEIGHT = 720
    
    # default height for thumbs
    SHOTGUN_THUMBNAIL_TARGET_HEIGHT = 400
    
    # the department to use for versions
    SHOTGUN_DEPARTMENT = "Flame"
    
    def __init__(self):
        """
        Constructor
        """
        self._app = sgtk.platform.current_bundle()

    def register_batch_publish(self, context, path, comments, version_number):
        """
        Creates a publish record in Shotgun for a Flame batch file.
        
        :param context: Context to associate the publish with
        :param path: Path to the batch file on disk
        :param comments: Details about the publish
        :param version_number: The version number to use
        :returns: Shotgun data for the created item
        """
        self._app.log_debug("Creating batch publish in Shotgun...")                
        publish_type = self._app.get_setting("batch_publish_type")
                                
        # put together a name for the publish. This should be on a form without a version
        # number, so that it can be used to group together publishes of the same kind, but
        # with different versions.
        # e.g. 'sequences/{Sequence}/{Shot}/editorial/flame/batch/{Shot}.v{version}.batch'
        batch_template = self._app.get_template("batch_template")
        fields = batch_template.get_fields(path)
        publish_name = fields.get("Shot")

        # now start assemble publish parameters
        args = {
            "tk": self._app.sgtk,
            "context": context,
            "comment": comments,
            "path": path,
            "name": publish_name,
            "version_number": version_number,
            "created_by": context.user,
            "task": context.task,
            "published_file_type": publish_type,
        }

        self._app.log_debug("Register publish in Shotgun: %s" % str(args))
        sg_publish_data = sgtk.util.register_publish(**args)
        self._app.log_debug("Register complete: %s" % sg_publish_data)
        return sg_publish_data

    def register_video_publish(self, export_preset, context, width, height, path, comments, version_number, is_batch_render):
        """
        Creates a publish record in Shotgun for a Flame video file.
        Optionally also creates a second publish record for an equivalent local quicktime

        :param export_preset: The export preset associated with this publish
        :param context: Context to associate the publish with
        :param width: the width of the images given by path
        :param height: the height of the images given by path
        :param path: Flame-style path to the frame sequence
        :param comments: Details about the publish
        :param version_number: The version number to use
        :param is_batch_render: If set to True, the publish is generated from a Batch render
        :returns: Shotgun data for the created item
        """
        self._app.log_debug("Creating video publish in Shotgun for %s..." % path)
        
        # resolve export preset object
        preset_obj = self._app.export_preset_handler.get_preset_by_name(export_preset)

        # The video publish is the result of a Batch render
        if is_batch_render:
            publish_name = preset_obj.get_batch_render_publish_name(path)
        else:
            publish_name = preset_obj.get_render_publish_name(path)

        # now do the main sequence publish
        args = {
            "tk": self._app.sgtk,
            "context": context,
            "comment": comments,
            "version_number": version_number,
            "created_by": context.user,
            "task": context.task,
            "thumbnail_path": None,
            "path": path,
            "name": publish_name,
            "published_file_type": preset_obj.get_render_publish_type()
        }
                
        self._app.log_debug("Register render publish in Shotgun: %s" % str(args))
        sg_publish_data = sgtk.util.register_publish(**args)
        self._app.log_debug("Register complete: %s" % sg_publish_data)

        # return the sg data for the main publish
        return sg_publish_data

    def update_version_dependencies(self, version_id, sg_publish_data):
        """
        Updates the dependencies for a version in Shotgun.
        
        :param version_id: Shotgun id for version to update
        :param sg_publish_data: Dictionary with type/id keys to connect.
        """
        data = {}
        
        # link to the publish
        if sgtk.util.get_published_file_entity_type(self._app.sgtk) == "PublishedFile":
            # client is using published file entity
            data["published_files"] = [sg_publish_data]
        else:
            # client is using old "TankPublishedFile" entity
            data["tank_published_file"] = sg_publish_data
            
        self._app.log_debug("Updating dependencies for version %s: %s" % (version_id, data))
        self._app.shotgun.update("Version", version_id, data)
        self._app.log_debug("...version update complete")

    def create_version(self, context, path, user_comments, sg_publish_data, aspect_ratio):        
        """
        Creates a single version record in Shotgun.
        
        Note: If you are creating more than one version at the same time, use 
              create_version_batch for performance.
                
        :param context: The context for the shot that the submission is associated with, 
                        in serialized form.
        :param path: Path to frames, Flame style path with [1234-1234] sequence marker.
        :param user_comments: Comments entered by the user at export start.
        :param sg_publish_data: Std Shotgun dictionary (with type and id), representing the publish
                                in Shotgun that has been carried out for this asset.
        :param aspect_ratio: Aspect ratio of the images
        :returns: The created Shotgun record
        """
        self._app.log_debug("Preparing data for version creation in Shotgun...")
        sg_batch_payload = []
        version_batch = self.create_version_batch(context, path, user_comments, sg_publish_data, aspect_ratio)
        sg_batch_payload.append(version_batch)
        self._app.log_debug("Create version in Shotgun: %s" % pprint.pformat(sg_batch_payload))
        sg_data = self._app.shotgun.batch(sg_batch_payload)
        self._app.log_debug("...done!")
        return sg_data[0]

    def create_version_batch(self, context, path, user_comments, sg_publish_data, aspect_ratio):
        """
        Similar to create_version(), but instead generates a single batch dictionary to be used
        within a Shotgun batch call. Takes the same parameters as create_version()

        :param context: The context for the shot that the submission is associated with, 
                        in serialized form.
        :param path: Path to frames, Flame style path with [1234-1234] sequence marker.
        :param user_comments: Comments entered by the user at export start.
        :param sg_publish_data: Std Shotgun dictionary (with type and id), representing the publish
                                in Shotgun that has been carried out for this asset.
        :param aspect_ratio: Aspect ratio of the images        
        :returns: dictionary suitable to be used as part of a Shotgun batch call
        """
        
        batch_item = {"request_type": "create",
                      "entity_type": "Version",
                      "data": {}}
        
        # let the version name be the main file name of the plate
        # /path/to/filename -> filename
        # /path/to/filename.ext -> filename
        # /path/to/filename.%04d.ext -> filename
        file_name = os.path.basename(path)
        version_name = os.path.splitext(os.path.splitext(file_name)[0])[0]
        batch_item["data"]["code"] = version_name
        
        batch_item["data"]["description"] = user_comments
        batch_item["data"]["project"] = context.project
        batch_item["data"]["entity"] = context.entity
        batch_item["data"]["created_by"] = context.user
        batch_item["data"]["user"] = context.user
        batch_item["data"]["sg_task"] = context.task
        
        # now figure out the frame numbers. For an initial Shotgun export this is easy because we have
        # access to the export profile which defines the frame offset which maps actual frames on disk with
        # frames in the cut space inside of Flame. However, for batch rendering, which is currently stateless,
        # this info is not available. It may be possible to extract it from the clip xml files, but for now,
        # lets keep it simple and look at the sequence file path to extract this data.
        #
        # Flame sequence tokens are on the form "[1001-1100]"
        try:
            re_match = re.search(".*\[([0-9]+)-([0-9]+)\]\..*", path)
            if re_match:
                (first_str, last_str) = re_match.groups()
                first_frame = int(first_str)
                last_frame = int(last_str)
            else:
                re_match = re.search(".*([0-9]+)\..*", path)
                if not re_match:
                    raise Exception("No frame number found")

                frame_str = re_match.group(1)
                first_frame = int(frame_str)
                last_frame = int(frame_str)

            # add frame data to version metadata
            batch_item["data"]["sg_first_frame"] = first_frame
            batch_item["data"]["sg_last_frame"] = last_frame
            batch_item["data"]["frame_count"] = last_frame - first_frame + 1
            batch_item["data"]["frame_range"] = "%s-%s" % (first_frame, last_frame)

        except Exception, e:
            self._app.log_warning("Could not extract frame data from path '%s'. "
                                  "Will proceed without frame data. Error reported: %s" % (path, e))

        batch_item["data"]["sg_frames_have_slate"] = False
        batch_item["data"]["sg_movie_has_slate"] = False
        batch_item["data"]["sg_frames_aspect_ratio"] = aspect_ratio
        batch_item["data"]["sg_movie_aspect_ratio"] = aspect_ratio

        # link to the publish
        if sg_publish_data:
            if sgtk.util.get_published_file_entity_type(self._app.sgtk) == "PublishedFile":
                # client is using published file entity
                batch_item["data"]["published_files"] = [sg_publish_data]
            else:
                # client is using old "TankPublishedFile" entity
                batch_item["data"]["tank_published_file"] = sg_publish_data
        
        # populate the path to frames with a path which is using %4d syntax
        batch_item["data"]["sg_path_to_frames"] = self.__get_tk_path_from_flame_plate_path(path)
        
        # This is used to find the latest Version from the same department.
        batch_item["data"]["sg_department"] = self.SHOTGUN_DEPARTMENT   
                    
        return batch_item

    def __get_tk_path_from_flame_plate_path(self, flame_path):
        """
        Given a xxx.[1234-1234].exr style Flame plate path,
        return the equivalent, normalized tk path, e.g. xxx.%04d.exr
        
        :param flame_path: Flame style plate path (must match the plate template)
        :returns: tk equivalent
        """
        template = self._app.sgtk.template_from_path(flame_path)
        
        if template is None:
            # the path does not match any template. This shouldn't happen since these
            # paths were all generated by the shotgun integration, however is possible because
            # of some known bugs in flame, where updated paths returned by flame hooks are not being
            # used by the flame system. A typical example is when a sequence name contains a space or
            # other special character - the toolkit template system will adjust the path to replace
            # spaces with underscores. These adjusted paths are returned to Flame but are not picked
            # up, resulting in the paths returned here not actually being valid.
            raise TankError("The path '%s' does not match any template in the Toolkit configuration. "
                            "This sometimes happens if Flame sequences or clips contain special characters "
                            "such as slashes or spaces." % flame_path)
        
        fields = template.get_fields(flame_path)
        fields["SEQ"] = "FORMAT: %d"
        fields["flame.frame"] = "FORMAT: %d"
        return template.apply_fields(fields)
