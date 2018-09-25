# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Flame Shot Exporter.

This app takes a sequence in Flame and generates lots of Shotgun related content.
It is similar to the Hiero exporter. The following items are generated:

- New Shots in Shotgun, with tasks
- Cut information in Shotgun
- New versions (with uploaded quicktimes) for all segments
- Plates on disk for each segment
- Batch files for each shot
- Clip xml files for shots and clips.

The exporter is effectively a wrapper around the Flame custom export process 
with some bindings to Shotgun.

This app implements two different sets of callbacks - both utilizing the same 
configuration and essentially parts of the same workflow (this is why they are not
split across two different apps).

- The Flame Shot export runs via a context menu item on the sequence right-click menu
- A Flare / batch mode render hook allows Shotgun to intercept the rendering process and
  ask the user if they want to submit to Shotgun review whenever they render out in Flame. 

"""

import uuid
import os
import re
import sgtk
import datetime
import pprint

from sgtk import TankError
from sgtk.platform import Application
    

class FlameExport(Application):
    """
    Export functionality to automate and streamline content export out of Flame.

    Details on Flame's data sent thru the exported hooks can be found at
    https://knowledge.autodesk.com/search-result/caas/CloudHelp/cloudhelp/2017/ENU/Flame-API/files/GUID-8EE47B4F-16F0-41D6-97BB-1226C0BDCC45-htm.html
    """

    def init_app(self):
        """
        Called as the application is being initialized.
        """
        self.log_debug("%s: Initializing" % self)
                
        # sequences that are being exported
        self._sequences = []
        
        # create a submit helper
        # because parts of this app runs on the farm, which doesn't have a UI,
        # there are two distinct modules on disk, one which is QT dependent and
        # one which isn't.
        export_utils = self.import_module("export_utils")
        self._sg_submit_helper = export_utils.ShotgunSubmitter()
        
        # batch render tracking - when doing a batch render, 
        # this is used to indicate that the user wants to send the render to review.
        self._send_batch_render_to_review = False
        
        # Shot export user UI input
        self._user_comments = ""
        self._export_preset = None

        # flag to indicate that something was actually submitted by the export process
        self._reached_post_asset_phase = False
        
        # load up our export presets
        # this wrapper class is used later on to access export presets in various ways
        self.export_preset_handler = export_utils.ExportPresetHandler()
        
        # register our desired interaction with Flame hooks
        # set up callbacks for the engine to trigger 
        # when this profile is being triggered
        menu_caption = self.get_setting("menu_name")        
        callbacks = {}
        callbacks["preCustomExport"] = self.pre_custom_export
        callbacks["preExportSequence"] = self.pre_export_sequence
        callbacks["preExportAsset"] = self.pre_export_asset
        callbacks["postExportAsset"] = self.post_export_asset
        callbacks["postCustomExport"] = self.do_submission_and_summary
        self.engine.register_export_hook(menu_caption, callbacks)
        
        # also register this app so that it runs after export in batch mode / Flare
        batch_callbacks = {}
        batch_callbacks["batchExportEnd"] = self.post_batch_render_sg_process
        batch_callbacks["batchExportBegin"] = self.pre_batch_render_checks
        self.engine.register_batch_hook(batch_callbacks)


    def _abort_export(self, info, message):
        info["abort"] = True
        info["abortMessage"] = message
        self.log_error(message)

    ##############################################################################################################
    # Flame shot export integration

    def pre_custom_export(self, session_id, info):
        """
        Flame hook called before a custom export begins. The export will be blocked
        until this function returns. This can be used to fill information that would
        have normally been extracted from the export window.
        
        :param info: Dictionary with info about the export. Contains the keys
                     - destinationHost: Host name where the exported files will be written to.
                     - destinationPath: Export path root.
                     - presetPath: Path to the preset used for the export.
                     - abort: Pass True back to Flame if you want to abort
                     - abortMessage: Abort message to feed back to client
        """
        from sgtk.platform.qt import QtGui
        
        # reset export session data
        self._sequences = []
        self._reached_post_asset_phase = False
        
        # pop up a UI asking the user for description
        dialogs = self.import_module("dialogs")
                      
        (return_code, widget) = self.engine.show_modal("Export Shots",
                                                       self,
                                                       dialogs.SubmitDialog,
                                                       self.export_preset_handler.get_preset_names())
        
        if return_code == QtGui.QDialog.Rejected:
            # user pressed cancel
            self._abort_export(info, "User cancelled the operation.")

        else:
            # get comments from user
            self._user_comments = widget.get_comments()
            # get export preset name
            export_preset_name = widget.get_video_preset()
            # resolve this to an object
            self._export_preset = self.export_preset_handler.get_preset_by_name(export_preset_name)
            
            # populate the host to use for the export. Currently hard coded to local
            info["destinationHost"] = self.engine.get_server_hostname()
            
            # let the export root path align with the primary project root
            info["destinationPath"] = self.sgtk.project_path
            
            # pick up the xml export profile from the configuration
            info["presetPath"] = self._export_preset.get_xml_path()    
            self.log_debug("%s: Starting custom export session with preset '%s'" % (self, info["presetPath"]))

        # Log usage metrics
        if hasattr(self, "log_metric"):
            # core supports metrics logging
            self.log_metric("Export", log_version=True)

    def pre_export_sequence(self, session_id, info):
        """
        Called from the Flame hooks before export.
        This is the time to set up the structure in Shotgun.
        
        :param session_id: String which identifies which export session is being referred to

        :param info: Information about the export. Contains the keys      
                     - destinationHost: Host name where the exported files will be written to.
                     - destinationPath: Export path root.
                     - sequenceName: Name of the exported sequence.
                     - shotNames: Tuple of all shot names in the exported sequence. 
                       Multiple segments could have the same shot name.
                     - abort: Hook can set this to True if the export sequence process should
                       be aborted. If other sequences are exported in the same export session
                       they will still be exported even if this export sequence is aborted.
                     - abortMessage: Error message to be displayed to the user when the export sequence
                       process has been aborted.
        """
        from sgtk.platform.qt import QtGui

        export_utils = self.import_module("export_utils")

        sequence_name = info["sequenceName"]
        shot_names = info["shotNames"]

        if len(shot_names) == 0:
            QtGui.QMessageBox.warning(None,
                                      "Please name your shots!",
                                      "The Shotgun integration requires you to name your shots. Please go back to "
                                      "the time line and ensure that all clips have been given shot names before "
                                      "proceeding!")
            self._abort_export(info, "Cannot export due to missing shot names.")
            return

        # @TODO - add more generic validation
        if " " in sequence_name:
            QtGui.QMessageBox.warning(None,
                                      "Sequence name cannot contain spaces!",
                                      "Your Sequence name contains spaces. This is currently not supported by "
                                      "the Shotgun/Flame integration. Try renaming your sequence and use for "
                                      "example underscores instead of spaces, then try again!")
            self._abort_export(info, "Cannot export due to spaces in sequence names.")
            return

        # set up object to represent sequence and shots
        sequence = export_utils.Sequence(sequence_name)
        for shot_name in shot_names:
            sequence.add_shot(shot_name)

        # create entities in Shotgun, create folders on disk and compute shot contexts.
        sequence.process_shotgun_shot_structure()
        self._sequences.append(sequence)

    
    def pre_export_asset(self, session_id, info):
        """
        Flame hook called when an item is about to be exported and a path needs to be computed.
        
        This will take the parameters from Flame, push them through the toolkit template
        system and then return a path to Flame that Flame will be using for the export.
 
        :param session_id: String which identifies which export session is being referred to.
                           This parameter makes it possible to distinguish between different 
                           export sessions running if this is needed (typically only needed for
                           expert use cases).

        :param info: Dictionary with a number of parameters:
        
           destinationHost: Host name where the exported files will be written to.
           destinationPath: Export path root.
           namePattern:     List of optional naming tokens.
           resolvedPath:    Full file pattern that will be exported with all the tokens resolved.
           assetName:       Name of the exported asset.
           sequenceName:    Name of the sequence the asset is part of.
           shotName:        Name of the shot the asset is part of.
           assetType:       Type of exported asset. ( 'video', 'movie', 'audio', 'batch', 'openClip', 'batchOpenClip' )
           width:           Frame width of the exported asset.
           height:          Frame height of the exported asset.
           aspectRatio:     Frame aspect ratio of the exported asset.
           depth:           Frame depth of the exported asset. ( '8-bits', '10-bits', '12-bits', '16 fp' )
           scanFormat:      Scan format of the exported asset. ( 'FIELD_1', 'FIELD_2', 'PROGRESSIVE' )
           fps:             Frame rate of exported asset.
           sequenceFps:     Frame rate of the sequence the asset is part of.
           sourceIn:        Source in point in frame and asset frame rate.
           sourceOut:       Source out point in frame and asset frame rate.
           recordIn:        Record in point in frame and sequence frame rate.
           recordOut:       Record out point in frame and sequence frame rate.
           handleIn:        Head as a frame, using the asset frame rate (fps key).
           handleOut:       Tail as a frame, using the asset frame rate (fps key).
           track:           ID of the sequence's track that contains the asset.
           trackName:       Name of the sequence's track that contains the asset.
           segmentIndex:    Asset index (1 based) in the track.
           versionName:     Current version name of export (Empty if unversioned).
           versionNumber:   Current version number of export (0 if unversioned).        
        """
        
        asset_type = info["assetType"]
        asset_name = info["assetName"]
        shot_name = info["shotName"]
        sequence_name = info["sequenceName"]

        if len(self._sequences) == 0:
            self._abort_export(info, "No sequence to export")
            return

        # only support the export of one sequence at a time
        sequence = self._sequences[-1]
        if sequence is None or sequence.name != sequence_name:
            self.log_error("Skipping unknown sequence %s" % sequence_name)
            return

        if asset_type not in ["video", 'movie', "batch", "batchOpenClip", "openClip"]:
            # the review system ignores any other assets. The export profiles are defined
            # in the app's settings hook, so technically there shouldn't be any other items
            # generated - but just in case there are (because of customizations), we'll simply
            # ignore these.
            return
        
        # check that the clip has a shot name - otherwise things won't work!
        if shot_name == "":       
            from sgtk.platform.qt import QtGui
            QtGui.QMessageBox.warning(
                None,
                "Missing shot name!",
                ("The clip '%s' does not have a shot name and therefore cannot be exported. "
                 "Please ensure that all shots you wish to exports "
                 "have been named. " % asset_name)
            )
            
            # TODO: send the clip to the trash for now. no way to abort at this point
            # but we don't have enough information to be able to proceed at this point either
            info["resolvedPath"] = "flame_trash/unnamed_shot_%s" % uuid.uuid4().hex
            
            # TODO: can we avoid this export altogether?
            return
        
        # prepare for export of asset
        shot = sequence.get_shot(shot_name)

        if asset_type in ["video", "movie"]:
            # resolve template for exported plates or video
            template = self._export_preset.get_render_template()
            
        elif asset_type == "batch":
            # resolve template for batch file
            template = self.get_template("batch_template")
            
        elif asset_type == "batchOpenClip":
            # resolve template for shot level open scene clip xml
            template = self.get_template("shot_clip_template")            

        elif asset_type == "openClip":
            # resolve template for segment level open scene clip xml
            template = self.get_template("segment_clip_template")

        self.log_debug("Attempting to resolve template %s..." % template)
        
        # resolve the fields out of the context
        self.log_debug("Resolving template %s using context %s" % (template, shot.context))
        fields = shot.context.as_template_fields(template)
        self.log_debug("Resolved context based fields: %s" % fields)
        
        if asset_type == "video":
            # handle the Flame sequence token - it will come in as "[1001-1100]"
            re_match = re.search(".*(\[[0-9]+-[0-9]+\])\..*", info["resolvedPath"])
            if re_match:
                frames = re_match.group(1)
                fields["SEQ"] = frames
                fields["flame.frame"] = frames

        # create some fields based on the info in the info params                
        if "versionNumber" in info:
            fields["version"] = int(info["versionNumber"])
        
        fields["segment_name"] = asset_name
            
        if "width" in info:
            fields["width"] = int(info["width"])

        if "height" in info:
            fields["height"] = int(info["height"])
        
        # populate the time field metadata
        now = datetime.datetime.now()
        fields["YYYY"] = now.year
        fields["MM"] = now.month
        fields["DD"] = now.day
        fields["hh"] = now.hour
        fields["mm"] = now.minute
        fields["ss"] = now.second
        
        try:
            full_path = template.apply_fields(fields)
        except Exception, e:
            raise TankError("Could not resolve a file system path " 
                            "from template %s and fields %s: %s" % (template, fields, e))
        
        self.log_debug("Resolved %s -> %s" % (fields, full_path))
        
        # chop off the root of the path - the resolvedPath should be local to the destinationPath
        local_path = full_path[len(info["destinationPath"])+1:]
        
        self.log_debug("Chopping off root path %s -> %s" % (full_path, local_path))
        
        # pass an updated path back to the Flame. This ensures that all the 
        # character substitutions etc are handled according to the toolkit logic
        info["resolvedPath"] = local_path

    def post_export_asset(self, session_id, info):
        """
        Flame hook called when an item has been exported.

        :param session_id: String which identifies which export session is being referred to.
                           This parameter makes it possible to distinguish between different 
                           export sessions running if this is needed (typically only needed for
                           expert use cases).

        :param info: Dictionary with a number of parameters:

           destinationHost: Host name where the exported files will be written to.
           destinationPath: Export path root.
           namePattern:     List of optional naming tokens.
           resolvedPath:    Full file pattern that will be exported with all the tokens resolved.
           assetName:       Name of the exported asset.
           sequenceName:    Name of the sequence the asset is part of.
           shotName:        Name of the shot the asset is part of.
           assetType:       Type of exported asset. ( 'video', 'movie', 'audio', 'batch', 'openClip', 'batchOpenClip' )
           isBackground:    True if the export of the asset happened in the background.
           backgroundJobId: Id of the background job given by the backburner manager upon submission. 
                            Empty if job is done in foreground.
           width:           Frame width of the exported asset.
           height:          Frame height of the exported asset.
           aspectRatio:     Frame aspect ratio of the exported asset.
           depth:           Frame depth of the exported asset. ( '8-bits', '10-bits', '12-bits', '16 fp' )
           scanFormat:      Scan format of the exported asset. ( 'FIELD_1', 'FIELD_2', 'PROGRESSIVE' )
           fps:             Frame rate of exported asset.
           sequenceFps:     Frame rate of the sequence the asset is part of.
           sourceIn:        Source in point in frame and asset frame rate.
           sourceOut:       Source out point in frame and asset frame rate.
           recordIn:        Record in point in frame and sequence frame rate.
           recordOut:       Record out point in frame and sequence frame rate.
           handleIn:        Head as a frame, using the asset frame rate (fps key).
           handleOut:       Tail as a frame, using the asset frame rate (fps key).
           track:           ID of the sequence's track that contains the asset.
           trackName:       Name of the sequence's track that contains the asset.
           segmentIndex:    Asset index (1 based) in the track.       
           versionName:     Current version name of export (Empty if unversioned).
           versionNumber:   Current version number of export (0 if unversioned).
        """
        asset_type = info["assetType"]
        segment_name = info["assetName"]
        shot_name = info["shotName"]
        sequence_name = info["sequenceName"]

        if asset_type not in ["video", 'movie', "batch"]:
            # ignore anything that isn't video or batch
            return
        
        # resolve shot object
        shot = self._sequences[-1].get_shot(shot_name)

        if asset_type in ["video", "movie"]:
            # create a new segment for the shot
            segment = shot.add_segment(segment_name)

            # note: not all versions of Flame pass a handle parameter
            # so add the preset default in case value isn't passed.
            if "handleIn" not in info:
                info["handleIn"] = self._export_preset.get_handles_length()

            if "handleOut" not in info:
                info["handleOut"] = self._export_preset.get_handles_length()

            # pass in raw data from flame
            segment.set_flame_data(info)

        elif asset_type == "batch":
            # this is a batch export. These are per *shot*, even in the case of a shot
            # with multiple clips, only one batch file gets output.
            shot.set_flame_batch_data(info)

        # indicate that the export has reached its last stage
        self._reached_post_asset_phase = True


    def do_submission_and_summary(self, session_id, info):
        """
        Flame hook which will push info to Shotgun and display a summary UI.

        :param session_id: String which identifies which export session is being referred to.
                           This parameter makes it possible to distinguish between different 
                           export sessions running if this is needed (typically only needed for
                           expert use cases).
        
        :param info: Information about the export. Contains the keys      
                     - destinationHost: Host name where the exported files will be written to.
                     - destinationPath: Export path root.
                     - presetPath: Path to the preset used for the export.
        """
        dialogs = self.import_module("dialogs")

        # if we haven't reached the post export stage, that means that something
        # has gone wrong along the way. Display the "oops, something went wrong" 
        # dialog.
        if not self._reached_post_asset_phase:
            self.engine.show_modal(
                "Submission Failed",
                self,
                dialogs.SubmissionFailedDialog
            )
            return

        num_cut_changes = 0
        num_created_shots = 0
        # figure out which shots are new
        for sequence in self._sequences:
            created_shots = [shot for shot in sequence.shots if shot.new_in_shotgun]
            num_created_shots += len(created_shots)

            # push shot cut changes and version records to shotgun
            # as a single batch call
            shotgun_batch_items = []
            version_path_lookup = {}

            # make sure all shots have their frame in/outs set correctly
            shotgun_batch_items += sequence.compute_shot_cut_changes()
            num_cut_changes += len(shotgun_batch_items)

            # create versions for all segments
            self.log_debug("Looping over all shots and segments to submit versions...")
            for shot in sequence.shots:
                for segment in shot.segments:

                    # it is possible that the user has manually cancelled the process, so
                    # it's possible that a segment doesn't have a video export associated
                    # this can happen if for example a user chooses not to overwrite an
                    # existing file on disk.
                    if segment.has_render_export:

                        # compute a version-create Shotgun batch dictionary
                        sg_version_batch = self._sg_submit_helper.create_version_batch(
                            shot.context,
                            segment.render_path,
                            self._user_comments,
                            None,
                            segment.render_aspect_ratio
                        )
                        # append to our main batch listing
                        self.log_debug("Registering version: %s" % pprint.pformat(sg_version_batch))
                        shotgun_batch_items.append(sg_version_batch)

                        # once the batch has been executed and the versions have been created in Shotgun
                        # we need to update our segment metadata with the Shotgun version id.
                        # in order to do that, maintain a lookup dictionary:
                        path_to_frames = sg_version_batch["data"]["sg_path_to_frames"]
                        version_path_lookup[path_to_frames] = segment

            # push all new versions and cut changes to Shotgun in a single batch call.
            sg_data = []
            if len(shotgun_batch_items) > 0:
                self.engine.show_busy("Updating Shotgun...", "Registering review and cut data...")
                try:
                    self.log_debug("Pushing %s Shotgun batch items..." % len(shotgun_batch_items))
                    sg_data = self.shotgun.batch(shotgun_batch_items)
                    self.log_debug("...done")
                finally:
                    # kill progress indicator
                    self.engine.clear_busy()

            # Update segment metadata with created Shotgun version ids so we can access it later
            for sg_entity in sg_data:
                if sg_entity["type"] == "Version":
                    # using our lookup table, find the metadata object
                    segment = version_path_lookup[sg_entity["sg_path_to_frames"]]
                    segment.set_shotgun_version_id(sg_entity["id"])

            # now that we have resolved all cut changes and created versions,
            # request the creation of a new cut in Shotgun
            sequence.create_cut(self._export_preset.get_cut_type())

            # Now submit a series of backburner jobs to handle the rest of the processing.

            # Submit single backburner job to register publishes
            # publish records are created for all renders and batch files
            sg_publishes = []

            self.log_debug("Looping over all shots and segments to submit publishes...")
            try:
                try:
                    for shot in sequence.shots:

                        # first see if we have a batch file being exported for this shot
                        if shot.has_batch_export:
                            self.engine.show_busy("Updating Shotgun...", "Updating Shot %s / Batch Setup" % (shot.name))
                            sg_batch_data = self._sg_submit_helper.register_batch_publish(
                                shot.context,
                                shot.batch_path,
                                self._user_comments,
                                shot.batch_version_number
                            )
                        else:
                            sg_batch_data = None

                        for segment in shot.segments:
                            if segment.has_render_export:
                                self.engine.show_busy("Updating Shotgun...", "Updating Shot %s / Segment %s" % (shot.name, segment.name))
                                sg_data = self._sg_submit_helper.register_video_publish(
                                    self._export_preset.get_name(),
                                    shot.context,
                                    segment.render_width,
                                    segment.render_height,
                                    segment.render_path,
                                    self._user_comments,
                                    segment.render_version_number,
                                    is_batch_render=False
                                )

                                # if the video media is generated in a backburner job, make sure that
                                # our quicktime job is executed *after* this job has finished
                                dependencies = segment.backburner_job_id

                                target_entities = [
                                    {
                                        "type": sg_data["type"],
                                        "id": sg_data["id"]
                                    }
                                ]
                                if segment.has_shotgun_version:
                                    target_entities.append(
                                        {
                                            "type": "Version",
                                            "id": segment.shotgun_version_id
                                        }
                                    )
                                if sg_batch_data is not None:
                                    target_entities.append(
                                        {
                                            "type": sg_batch_data["type"],
                                            "id": sg_batch_data["id"]
                                        }
                                    )
                                    sg_batch_data = None

                                self.engine.thumbnail_generator.generate(
                                    display_name=segment.name,
                                    path=segment.render_path,
                                    dependencies=dependencies,
                                    target_entities=target_entities,
                                    asset_info=segment.flame_data,
                                    favor_preview=self._export_preset.upload_quicktime()
                                )
                finally:
                    # The thumbnail generator will bundle request for same paths to
                    # avoid rendering multiple time the same asset. We must call
                    # finalize to actually send the job requests
                    #
                    self.engine.show_busy("Updating Shotgun...", "Updating thumbnails...")
                    self.engine.thumbnail_generator.finalize()
            finally:
                self.engine.clear_busy()

            # For each segment, generate a high res quicktime (for local playback in say RV)
            # Each item will be processed in a separate backburner job.
            # note that this happens in a separate loop after the upload quicktime loop
            # to ensure that these tasks happen last.
            if self._export_preset.highres_quicktime_enabled():
                try:
                    self.engine.show_busy("Updating Shotgun...", "Generating high-res quicktimes...")
                    self.log_debug("Looping over all shots and segments to generate high-res quicktimes...")
                    for shot in sequence.shots:
                        for segment in shot.segments:
                            if segment.has_shotgun_version:

                                # compute quicktime path from frames
                                quicktime_path = self._export_preset.quicktime_path_from_render_path(
                                    segment.render_path
                                )

                                # if the video media is generated in a backburner job, make sure that
                                # our quicktime job is executed *after* this job has finished
                                dependencies = segment.backburner_job_id

                                args = {
                                    "export_preset_name": self._export_preset.get_name(),
                                    "version_id": segment.shotgun_version_id,
                                    "path": segment.render_path,
                                    "quicktime_path": quicktime_path,
                                    "width": segment.render_width,
                                    "height": segment.render_height,
                                    "fps": segment.fps
                                }

                                target_entities = [
                                    {
                                        "type": "Version",
                                        "id": segment.shotgun_version_id
                                    }
                                ]

                                # Generate a movie file that will not be uploaded to
                                # Shotgun server but instead will be linked using the
                                # Path to Movie field.
                                #
                                self.engine.local_movie_generator.generate(
                                    src_path=segment.render_path,
                                    dst_path=quicktime_path,
                                    display_name=segment.name,
                                    target_entities=target_entities,
                                    asset_info=segment.flame_data,
                                    dependencies=dependencies
                                )
                finally:
                    self.engine.clear_busy()

        # now, as a last step, show a summary UI to the user, including a
        # very brief overview of what changes have been carried out.
        comments = "Your export has been pushed to the Backburner queue for processing.<br><br>"
        
        if num_created_shots == 1:
            comments += "- A new Shot was created in Shotgun. <br>"
        elif num_created_shots > 1:
            comments += "- %d new Shots were created in Shotgun. <br>" % num_created_shots 

        num_cut_updates = (num_cut_changes - num_created_shots)
        if num_cut_updates == 1:
            comments += "- One Shot had its cut information updated. <br>"
        elif num_cut_updates > 1:
            comments += "- %d Shots had their cut information updated. <br>" % num_cut_updates 

        self.engine.show_modal(
            "Submission Complete",
            self,
            dialogs.SubmissionCompleteDialog,
            comments
        )





    ##############################################################################################################
    # Flare / batch mode integration

    def pre_batch_render_checks(self, info):
        """
        Flame hook called before rendering starts in batch/Flare.
        
        This pops up a UI asking the user if they want to send things to review.
        
        :param info: Dictionary with a number of parameters:
        
            nodeName:             Name of the export node.   
            exportPath:           Export path as entered in the application UI.
                                  Can be modified by the hook to change where the file are written.
            namePattern:          List of optional naming tokens as entered in the application UI.
            resolvedPath:         Full file pattern that will be exported with all the tokens resolved.
            firstFrame:           Frame number of the first frame that will be exported.
            lastFrame:            Frame number of the last frame that will be exported.
            versionName:          Current version name of export (Empty if unversioned).
            versionNumber:        Current version number of export (0 if unversioned).
            openClipNamePattern:  List of optional naming tokens pointing to the open clip created if any
                                  as entered in the application UI. This is only available if versioning
                                  is enabled.
            openClipResolvedPath: Full path to the open clip created if any with all the tokens resolved.
                                  This is only available if versioning is enabled.
            setupNamePattern:     List of optional naming tokens pointing to the setup created if any
                                  as entered in the application UI. This is only available if versioning
                                  is enabled.
            setupResolvedPath:    Full path to the setup created if any with all the tokens resolved.
                                  This is only available if versioning is enabled.
            aborted:              Indicate if the export has been aborted by the user.
            lastFrame:            Last frame rendered
            firstFrame:           First frame rendered
            fps:                  Frame rate of render
            aspectRatio:          Frame aspect ratio
            width:                Frame width
            height:               Frame height
            depth:                Frame depth ( '8-bits', '10-bits', '12-bits', '16 fp' )
            scanFormat:           Scan format ( 'FIELD_1', 'FIELD_2', 'PROGRESSIVE' )        
        """
        
        # these member variables are used to pass data down the pipeline, to post_batch_render_sg_process()
        self._send_batch_render_to_review = False
        self._user_comments = None
        self._batch_export_preset = None
        self._batch_context = None
        
        render_path = os.path.join(info.get("exportPath"), info.get("resolvedPath"))
        batch_path = info.get("setupResolvedPath")

        # first check if the resolved paths match our templates in the settings. Otherwise ignore the export
        self.log_debug("Checking if the render path '%s' is recognized by toolkit..." % render_path)
        self._batch_export_preset = self.export_preset_handler.get_preset_for_batch_render_path(render_path)
        if self._batch_export_preset is None:
            self.log_debug("This path does not appear to match any toolkit render paths. Ignoring.")
            return None
        
        batch_template = self.get_template("batch_template")
        if not batch_template.validate(batch_path):
            self.log_debug("The path '%s' does not match the template '%s'. Ignoring." % (batch_path, batch_template))
            return None

        # as a last check, extract the context for the batch path
        self.log_debug("Getting context from path '%s'" % batch_path)
        context = self.sgtk.context_from_path(batch_path)
        self.log_debug("Context: %s" % context)
        if context is None:
            # not known by this app
            self.log_debug("Could not establish a context from the batch path. Aborting.")
            return

        # looks like we understand these paths!
        # store context so we can pass it downstream to the submission method.
        self._batch_context = context

        # ok so this looks like one of our renders - check with the user if they want to submit to review!
        from sgtk.platform.qt import QtGui

        # pop up a UI asking the user for description
        dialogs = self.import_module("dialogs")
        (return_code, widget) = self.engine.show_modal(
            "Send to Review",
            self,
            dialogs.BatchRenderDialog
        )

        if return_code != QtGui.QDialog.Rejected:
            # user wants review!
            self._send_batch_render_to_review = True
            self._user_comments = widget.get_comments()


    def post_batch_render_sg_process(self, info):
        """
        Flame hook called when batch rendering has finished.
        
        :param info: Dictionary with a number of parameters:
        
            nodeName:             Name of the export node.   
            exportPath:           Export path as entered in the application UI.
                                  Can be modified by the hook to change where the file are written.
            namePattern:          List of optional naming tokens as entered in the application UI.
            resolvedPath:         Full file pattern that will be exported with all the tokens resolved.
            firstFrame:           Frame number of the first frame that will be exported.
            lastFrame:            Frame number of the last frame that will be exported.
            versionName:          Current version name of export (Empty if unversioned).
            versionNumber:        Current version number of export (0 if unversioned).
            openClipNamePattern:  List of optional naming tokens pointing to the open clip created if any
                                  as entered in the application UI. This is only available if versioning
                                  is enabled.
            openClipResolvedPath: Full path to the open clip created if any with all the tokens resolved.
                                  This is only available if versioning is enabled.
            setupNamePattern:     List of optional naming tokens pointing to the setup created if any
                                  as entered in the application UI. This is only available if versioning
                                  is enabled.
            setupResolvedPath:    Full path to the setup created if any with all the tokens resolved.
                                  This is only available if versioning is enabled.
            aborted:              Indicate if the export has been aborted by the user.
            lastFrame:            Last frame rendered
            firstFrame:           First frame rendered
            fps:                  Frame rate of render
            aspectRatio:          Frame aspect ratio
            width:                Frame width
            height:               Frame height
            depth:                Frame depth ( '8-bits', '10-bits', '12-bits', '16 fp' )
            scanFormat:           Scan format ( 'FIELD_1', 'FIELD_2', 'PROGRESSIVE' )
            aborted:              Indicate if the export has been aborted by the user.
        """

        if info.get("aborted"):
            self.log_debug("Rendering was aborted. Will not push to Shotgun.")
            return

        if self._batch_export_preset is None:
            self.log_warning("Batch export preset was not populated in the pre-batch render hook. "
                             "Aborting post batch render hook.")
            return

        version_number = int(info["versionNumber"])
        description = self._user_comments or "Automatic Flame batch render"
        export_preset_obj = self.export_preset_handler.get_preset_by_name(self._batch_export_preset.get_name())

        # first register the batch file as a publish in Shotgun
        batch_path = info.get("setupResolvedPath")
        self._sg_submit_helper.register_batch_publish(self._batch_context, batch_path, description, version_number)

        try:
            self.engine.show_busy("Updating Shotgun...", "Publishing...")

            # Now register the rendered images as a published plate in Shotgun
            full_flame_batch_render_path = os.path.join(info.get("exportPath"), info.get("resolvedPath"))
            
            sg_data = self._sg_submit_helper.register_video_publish(
                export_preset_obj.get_name(),
                self._batch_context,
                info["width"],
                info["height"],
                full_flame_batch_render_path,
                description,
                version_number,
                is_batch_render=True
            )

            target_entities = [
                {
                    "type": sg_data["type"],
                    "id" : sg_data["id"]
                }
            ]

            # Finally, create a version record in Shotgun, generate a quicktime and upload it
            # only do this if the user clicked "send to review" in the UI.
            if self._send_batch_render_to_review:
                sg_version_data = self._sg_submit_helper.create_version(
                    self._batch_context,
                    full_flame_batch_render_path,
                    description,
                    sg_data,
                    info["aspectRatio"]
                )

                target_entities.append(
                    {
                        "type": "Version",
                        "id" : sg_version_data["id"]
                    }
                )

                if export_preset_obj.batch_highres_quicktime_enabled():
                    self.engine.show_busy("Updating Shotgun...", "Updating local quicktime...")
                    self.engine.trancoder.trancoder(
                        display_name=export_preset_obj.get_name(),
                        path=full_flame_batch_render_path,
                        target_entities=target_entities,
                        asset_info=info
                    )

            self.engine.show_busy("Updating Shotgun...", "Updating thumbnails...")
            self.engine.thumbnail_generator.generate(
                display_name=export_preset_obj.get_name(),
                path=full_flame_batch_render_path,
                dependencies=None,
                target_entities=target_entities,
                asset_info=info,
                favor_preview=export_preset_obj.upload_quicktime()
            )
            self.engine.thumbnail_generator.finalize()
        finally:
            self.engine.clear_busy()
