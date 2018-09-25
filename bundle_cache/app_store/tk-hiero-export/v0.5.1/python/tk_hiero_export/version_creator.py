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
import ast
import sys
import shutil
import tempfile
import inspect

from hiero.exporters import FnExternalRender
from hiero.exporters import FnTranscodeExporter
from hiero.exporters import FnTranscodeExporterUI

import hiero
from hiero import core
from hiero.core import *

import tank
import sgtk.util
from sgtk.platform.qt import QtGui, QtCore

from .base import ShotgunHieroObjectBase
from .collating_exporter import CollatingExporter, CollatedShotPreset

from . import (
    HieroGetQuicktimeSettings,
    HieroGetShot,
    HieroUpdateVersionData,
    HieroGetExtraPublishData,
    HieroPostVersionCreation,
)


class ShotgunTranscodeExporterUI(ShotgunHieroObjectBase, FnTranscodeExporterUI.TranscodeExporterUI):
    """
    Custom Preferences UI for the shotgun transcoder

    Embeds the UI for the std transcoder UI.
    """
    def __init__(self, preset):
        FnTranscodeExporterUI.TranscodeExporterUI.__init__(self, preset)
        self._displayName = "Shotgun Transcode Images"
        self._taskType = ShotgunTranscodeExporter

    def create_version_changed(self, state):
        create_version = (state == QtCore.Qt.Checked)
        self._preset._properties["create_version"] = create_version

    def populateUI(self, widget, exportTemplate):

        # prior to 10.5v1, this method created the layout. in 10.5v1 and later,
        # the widget already has a layout
        if self.app.get_nuke_version_tuple() >= (10, 5, 1):
            layout = widget.layout()
        else:
            # create a layout with custom top and bottom widgets
            layout = QtGui.QVBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(9)

        top = QtGui.QWidget()

        top_layout = QtGui.QVBoxLayout()
        top_layout.setContentsMargins(9, 0, 9, 0)
        create_version_checkbox = QtGui.QCheckBox("Create Shotgun Version", widget)
        create_version_checkbox.setToolTip(
            "Create a Version in Shotgun for this transcode.\n\n"
            "If the output format is not a quicktime, then\n"
            "a quicktime will be created.  The quicktime will\n"
            "be uploaded to Shotgun as Screening Room media."
        )

        create_version_checkbox.setCheckState(QtCore.Qt.Checked)
        if not self._preset._properties.get("create_version", True):
            create_version_checkbox.setCheckState(QtCore.Qt.Unchecked)
        create_version_checkbox.stateChanged.connect(self.create_version_changed)
        top_layout.addWidget(create_version_checkbox)

        top.setLayout(top_layout)

        middle = QtGui.QWidget()

        # prior to 10.5v1, the layout was set in the base class. in 10.5v1, the
        # base class expects the widget to already have a layout.
        if self.app.get_nuke_version_tuple() >= (10, 5, 1):
            middle.setLayout(QtGui.QVBoxLayout())

        # populate the middle with the standard layout
        FnTranscodeExporterUI.TranscodeExporterUI.populateUI(self, middle, exportTemplate)

        layout.addWidget(top)
        layout.addWidget(middle)

        # Handle any custom widget work the user did via the custom_export_ui
        # hook.
        custom_widget = self._get_custom_widget(
            parent=widget,
            create_method="create_transcode_exporter_widget",
            get_method="get_transcode_exporter_ui_properties",
            set_method="set_transcode_exporter_ui_properties",
        )

        if custom_widget is not None:
            layout.addWidget(custom_widget)



class ShotgunTranscodeExporter(ShotgunHieroObjectBase, FnTranscodeExporter.TranscodeExporter, CollatingExporter):
    """
    Create Transcode object and send to Shotgun
    """
    def __init__(self, initDict):
        """ Constructor """
        FnTranscodeExporter.TranscodeExporter.__init__(self, initDict)
        CollatingExporter.__init__(self)
        self._resolved_export_path = None
        self._sequence_name = None
        self._shot_name = None
        self._thumbnail = None
        self._quicktime_path = None
        self._temp_quicktime = None

    def buildScript(self):
        """
        Override the default buildScript functionality to also output a temp movie
        file if needed for uploading to Shotgun
        """

        # This is a bit of a hack to account for some changes to the
        # transcode exporter that ships with Nuke/Hiero 9.0 compared
        # to earlier versions of Hiero.
        file_type = self._preset.properties()['file_type']
        if file_type in ["mov", "ffmpeg"]:
            if not self._preset.properties()[file_type].get("encoder"):
                encoder_name = self.app.get_default_encoder_name()
                self._preset.properties()[file_type]["encoder"] = encoder_name

        # Build the usual script
        FnTranscodeExporter.TranscodeExporter.buildScript(self)

        # If we are not creating a version then we do not need the extra node
        if not self._preset.properties()['create_version']:
            return

        if file_type in ["mov", "ffmpeg"]:
            # already outputting a mov file, use that for upload
            self._quicktime_path = self.resolvedExportPath()
            self._temp_quicktime = False
            return

        self._quicktime_path = os.path.join(tempfile.mkdtemp(), 'preview.mov')
        self._temp_quicktime = True
        nodeName = "Shotgun Screening Room Media"

        framerate = None
        if self._sequence:
            framerate = self._sequence.framerate()
        if self._clip.framerate().isValid():
            framerate = self._clip.framerate()

        preset = FnTranscodeExporter.TranscodePreset("Qt Write", self._preset.properties())

        # insert the write node to generate the quicktime
        file_type, properties = self.app.execute_hook(
            "hook_get_quicktime_settings",
            for_shotgun=True,
            base_class=HieroGetQuicktimeSettings,
        )
        self.app.log_info("Transcode quicktime settings: %s" % (properties,))
        preset.properties().update({
            "file_type": file_type,
            file_type: properties,
        })

        # Sadly Foundry has a habit of changing the interfaces of
        # their Python classes out from under us, so now we're going
        # to have to handle this the ugly way, via introspecting the
        # arguments expected by the createWriteNode method.
        arg_spec = inspect.getargspec(FnExternalRender.createWriteNode)
        if "projectsettings" in arg_spec.args:
            kwargs = dict(
                path=self._quicktime_path,
                preset=preset,
                nodeName=nodeName,
                framerate=framerate,
                projectsettings=self._projectSettings,
            )
        elif "ctx" in arg_spec.args:
            kwargs = dict(
                ctx=self,
                path=self._quicktime_path,
                preset=preset,
                nodeName=nodeName,
                framerate=framerate,
                project=self._project,
            )
        else:
            kwargs = dict(
                path=self._quicktime_path,
                preset=preset,
                nodeName=nodeName,
                framerate=framerate,
                project=self._project,
            )
        mov_write_node = FnExternalRender.createWriteNode(**kwargs)
        self._script.addNode(mov_write_node)

    def sequenceName(self):
        """override default sequenceName() to handle collated shots"""
        try:
            if self.isCollated():
                return self._parentSequence.name()
            else:
                return FnTranscodeExporter.TranscodeExporter.sequenceName(self)
        except AttributeError:
            return FnTranscodeExporter.TranscodeExporter.sequenceName(self)

    def writeAudio(self):
        """
        Overridden method to allow proper timings for audio export
        """
        item = self._item
        if item.guid() in self._collatedItemsMap:
            item = self._collatedItemsMap[item.guid()]

        # Call parent method with swapped items in order to get proper timings
        original = self._item
        self._item = item
        
        result = FnTranscodeExporter.TranscodeExporter.writeAudio(self)

        self._item = original

        return result

    def startTask(self):
        """ Run Task """
        if self._resolved_export_path is None:
            self._resolved_export_path = self.resolvedExportPath()
            self._tk_version = self._formatTkVersionString(self.versionString())
            self._sequence_name = self.sequenceName()

            # convert slashes to native os style..
            self._resolved_export_path = self._resolved_export_path.replace("/", os.path.sep)

        # call the get_shot hook
        ########################
        if self.app.shot_count == 0:
            self.app.preprocess_data = {}

        # associate publishes with correct shot, which will be the hero item
        # if we are collating
        if self.isCollated() and not self.isHero():
            item = self.heroItem()
        else:
            item = self._item

        # store the shot for use in finishTask. query the head/tail values set
        # on the shot updater task so that we can set those values on the
        # Version created later.
        self._sg_shot = self.app.execute_hook(
            "hook_get_shot",
            task=self,
            item=item,
            data=self.app.preprocess_data,
            fields=[
                "sg_head_in",
                "sg_tail_out"
            ],
            base_class=HieroGetShot,
        )

        # populate the data dictionary for our Version while the item is still valid
        ##############################
        # see if we get a task to use
        self._sg_task = None
        try:
            task_filter = self.app.get_setting("default_task_filter", "[]")
            task_filter = ast.literal_eval(task_filter)
            task_filter.append(["entity", "is", self._sg_shot])
            tasks = self.app.shotgun.find("Task", task_filter)
            if len(tasks) == 1:
                self._sg_task = tasks[0]
        except ValueError:
            # continue without task
            setting = self.app.get_setting("default_task_filter", "[]")
            self.app.log_error("Invalid value for 'default_task_filter': %s" % setting)

        if self._preset.properties()['create_version']:
            # lookup current login
            sg_current_user = tank.util.get_current_user(self.app.tank)

            file_name = os.path.basename(self._resolved_export_path)
            file_name = os.path.splitext(file_name)[0]
            file_name = file_name.capitalize()

            # use the head/tail to populate frame first/last/range fields on
            # the Version
            head_in = self._sg_shot["sg_head_in"]
            tail_out = self._sg_shot["sg_tail_out"]

            self._version_data = {
                "user": sg_current_user,
                "created_by": sg_current_user,
                "entity": self._sg_shot,
                "project": self.app.context.project,
                "sg_path_to_movie": self._resolved_export_path,
                "code": file_name,
                "sg_first_frame": head_in,
                "sg_last_frame": tail_out,
                "frame_range": "%s-%s" % (head_in, tail_out),
            }

            if self._sg_task is not None:
                self._version_data["sg_task"] = self._sg_task

            # call the update version hook to allow for customization
            self.app.execute_hook(
                "hook_update_version_data",
                version_data=self._version_data,
                task=self,
                base_class=HieroUpdateVersionData,
            )

        # call the publish data hook to allow for publish customization
        self._extra_publish_data = self.app.execute_hook(
            "hook_get_extra_publish_data",
            task=self,
            base_class=HieroGetExtraPublishData,
        )

        # figure out the thumbnail frame
        ##########################
        source = self._item.source()

        # If we can't get a thumbnail it isn't the end of the world.
        # When we get to the upload we'll do nothing if we don't have
        # anything to work with, which will result in the same result
        # as if the thumbnail failed to upload.
        try:
            self._thumbnail = source.thumbnail(self._item.sourceIn())
        except Exception:
            pass

        return FnTranscodeExporter.TranscodeExporter.startTask(self)

    def finishTask(self):
        """ Finish Task """
        # run base class implementation
        FnTranscodeExporter.TranscodeExporter.finishTask(self)

        # create publish
        ################
        # by using entity instead of export path to get context, this ensures
        # collated plates get linked to the hero shot
        ctx = self.app.tank.context_from_entity('Shot', self._sg_shot['id'])
        published_file_type = self.app.get_setting('plate_published_file_type')

        args = {
            "tk": self.app.tank,
            "context": ctx,
            "path": self._resolved_export_path,
            "name": os.path.basename(self._resolved_export_path),
            "version_number": int(self._tk_version),
            "published_file_type": published_file_type,
        }

        if self._sg_task is not None:
            args["task"] = self._sg_task

        published_file_entity_type = sgtk.util.get_published_file_entity_type(self.app.sgtk)

        # register publish
        self.app.log_debug("Register publish in shotgun: %s" % str(args))
        pub_data = tank.util.register_publish(**args)
        if self._extra_publish_data is not None:
            self.app.log_debug("Updating Shotgun %s %s" % (published_file_entity_type, str(self._extra_publish_data)))
            self.app.shotgun.update(pub_data["type"], pub_data["id"], self._extra_publish_data)

        # upload thumbnail for publish
        if self._thumbnail:
            self._upload_thumbnail_to_sg(pub_data, self._thumbnail)
        else:
            self.app.log_debug(
                "There was no thumbnail available for %s %s" % (
                    published_file_entity_type,
                    str(self._extra_publish_data)
                )
            )

        # create version
        ################
        vers = None
        if self._preset.properties()['create_version']:
            if published_file_entity_type == "PublishedFile":
                self._version_data["published_files"] = [pub_data]
            else:  # == "TankPublishedFile
                self._version_data["tank_published_file"] = pub_data

            self.app.log_debug("Creating Shotgun Version %s" % str(self._version_data))
            vers = self.app.shotgun.create("Version", self._version_data)

            if os.path.exists(self._quicktime_path):
                self.app.log_debug("Uploading quicktime to Shotgun... (%s)" % self._quicktime_path)
                self.app.shotgun.upload("Version", vers["id"], self._quicktime_path, "sg_uploaded_movie")
                if self._temp_quicktime:
                    shutil.rmtree(os.path.dirname(self._quicktime_path))

        # Post creation hook
        ####################
        if vers:
            self.app.execute_hook(
                "hook_post_version_creation",
                version_data=vers,
                base_class=HieroPostVersionCreation,
            )

        # Update the cut item if possible
        #################################
        if vers and hasattr(self, "_cut_item_data"):

            # a version was created and we have a cut item to update.

            # just make sure the cut item data has an id which should imply that
            # it was created in the db.
            if "id" in self._cut_item_data:
                cut_item_id = self._cut_item_data["id"]

                # update the Cut item with the newly uploaded version
                self.app.shotgun.update("CutItem", cut_item_id,
                    {"version": vers})
                self.app.log_debug("Attached version to cut item.")

                # upload a thumbnail for the cut item as well
                if self._thumbnail:
                    self._upload_thumbnail_to_sg(
                        {"type": "CutItem", "id": cut_item_id},
                        self._thumbnail
                    )

        # Log usage metrics
        try:
            self.app.log_metric("Transcode & Publish", log_version=True)
        except:
            # ingore any errors. ex: metrics logging not supported
            pass


class ShotgunTranscodePreset(ShotgunHieroObjectBase, FnTranscodeExporter.TranscodePreset, CollatedShotPreset):
    """ Settings for the shotgun transcode step """
    def __init__(self, name, properties):
        FnTranscodeExporter.TranscodePreset.__init__(self, name, properties)
        self._parentType = ShotgunTranscodeExporter
        CollatedShotPreset.__init__(self, self.properties())

        # set default values
        self._properties["create_version"] = True

        # Handle custom properties from the customize_export_ui hook.
        custom_properties = self._get_custom_properties(
            "get_transcode_exporter_ui_properties"
        ) or []

        self.properties().update({d["name"]: d["value"] for d in custom_properties})
