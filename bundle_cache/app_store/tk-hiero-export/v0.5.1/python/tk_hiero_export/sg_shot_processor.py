# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import itertools

import sgtk
from sgtk.platform.qt import QtGui

import hiero.core
from hiero.core import FnExporterBase

from hiero.exporters import FnShotProcessor

# For Hiero versions prior to 9.0 the ShotProcessor class
# contained both the execution and UI logic. That was split
# into two classes in 9.0. To maintain backwards compatibility
# but without duplicating code or breaking existing local
# export presets we've split into separate UI and Processor
# classes, but for the UI class we will fall back on using
# the ShotProcessor as the base class in cases where we are
# unable to import the separate ShotProcessorUI class that
# was introduced in 9.0.
try:
    from hiero.exporters.FnShotProcessorUI import ShotProcessorUI
except ImportError:
    ShotProcessorUI = FnShotProcessor.ShotProcessor

from .base import ShotgunHieroObjectBase
from .version_creator import ShotgunTranscodeExporter
from .shot_updater import ShotgunShotUpdaterPreset
from .shot_updater import ShotgunShotUpdater
from .collating_exporter import CollatedShotPreset
from .collating_exporter_ui import CollatingExporterUI

from . import (
    HieroPreExport,
    HieroUpdateCuts,
    HieroGetShot,
    HieroResolveCustomStrings,
)

from tank.errors import TankHookMethodDoesNotExistError


class ShotgunShotProcessorUI(ShotgunHieroObjectBase, ShotProcessorUI, CollatingExporterUI):
    """
    Add extra UI to the built in Shot processor.
    """
    def __init__(self, preset):
        ShotProcessorUI.__init__(self, preset)
        CollatingExporterUI.__init__(self)

    def displayName(self):
        return "Process as Shotgun Shots"

    def toolTip(self):
        return "Process as Shotgun Shots generates output on a per-shot basis and logs it in Shotgun."

    def populateUI(self, *args, **kwargs):
        """
        Create Settings UI.
        """

        # NOTE:
        # This method's signature changed in NukeStudio/Hiero 10.5v1. So
        # we account for it by parsing the args.
        if self.app.get_nuke_version_tuple() >= (10, 5, 1):
            (widget, taskUIWidget, exportItems) = args
        else:
            (widget, exportItems, editMode) = args

        # create a layout with custom top and bottom widgets
        master_layout = QtGui.QHBoxLayout(widget)
        master_layout.setContentsMargins(0, 0, 0, 0)

        # add group box for shotgun stuff
        shotgun_groupbox = QtGui.QGroupBox("Shotgun Shot and Sequence Creation Settings")
        master_layout.addWidget(shotgun_groupbox)
        shotgun_layout = QtGui.QVBoxLayout(shotgun_groupbox)

        # create some helpful text
        header_text = QtGui.QLabel()
        header_text.setWordWrap(True)
        header_text.setText(
            """
            <big>Welcome to the Shotgun Shot Exporter!</big>
            <p>When you are using the Shotgun Shot Processor, Shots and
            Sequences in Shotgun will be created based on the curent timeline.
            Existing Shots will be updated with the latest cut lengths.
            Quicktimes for each shot will be reviewable in the Media app when
            you use the special Shotgun Transcode plugin - all included and
            ready to go in the default preset.
            </p>
            """
        )
        shotgun_layout.addWidget(header_text)
        shotgun_layout.addSpacing(8)

        # make space for the spreadsheet
        spreadsheet_widget = QtGui.QWidget()
        shotgun_layout.addWidget(spreadsheet_widget)
        layout = QtGui.QHBoxLayout(spreadsheet_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        properties = self._preset.properties().get('shotgunShotCreateProperties', {})
        layout.addWidget(self._build_tag_selector_widget(exportItems, properties))
        layout.addStretch(1)

        footer_text = QtGui.QLabel()
        default_task_template = self.app.get_setting('default_task_template')
        footer_text.setText("<p>Shots without any tags will be assigned the '%s' task template.</p>" % default_task_template )
        shotgun_layout.addWidget(footer_text)

        # add collate options
        collating_widget = QtGui.QWidget()
        shotgun_layout.addWidget(collating_widget)
        CollatingExporterUI.populateUI(self, collating_widget, properties,
            cut_support=self._cutsSupported())

        if self._cutsSupported():
            cut_type_layout = self._build_cut_type_layout(properties)
            shotgun_layout.addLayout(cut_type_layout)

        shotgun_layout.addStretch()

        # add default settings from baseclass below
        default = QtGui.QWidget()
        master_layout.addWidget(default)

        # As noted above, the signature for this method changed in 10.5v1 so we
        # must account for it when calling the base class.
        if self.app.get_nuke_version_tuple() >= (10, 5, 1):
            ShotProcessorUI.populateUI(self, default, taskUIWidget, exportItems)
        else:
            ShotProcessorUI.populateUI(self, default, exportItems, editMode)

        # Handle any custom widget work the user did via the custom_export_ui
        # hook.
        custom_widget = self._get_custom_widget(
            parent=widget,
            create_method="create_shot_processor_widget",
            get_method="get_shot_processor_ui_properties",
            set_method="set_shot_processor_ui_properties",
            properties=self._preset.properties()["shotgunShotCreateProperties"],
        )

        if custom_widget is not None:
            layout.addWidget(custom_widget)

    def _build_cut_type_layout(self, properties):
        """
        Returns layout with a Label and QComboBox with a list of cut types.

        :param properties: A dict containing the 'sg_cut_type' preset
        :return: QtGui.QLayout - for the cut type widget
        """
        tooltip = "What to populate in the `Type` field for this Cut in Shotgun"

        # ---- construct the widget

        # populate the list of cut types and default from the site schema
        schema = self.app.shotgun.schema_field_read("Cut", "sg_cut_type")
        cut_types = schema["sg_cut_type"]["properties"]["valid_values"]["value"]

        # make sure we have an empty item at the top
        cut_types.insert(0, "")

        # create a combo box for the cut types
        cut_type_widget = QtGui.QComboBox()
        cut_type_widget.setToolTip(tooltip)
        cut_type_widget.addItems(cut_types)

        # make sure the current value is set
        current_value = properties["sg_cut_type"]
        index = cut_type_widget.findText(current_value)
        if index > 0:
            # found a match
            cut_type_widget.setCurrentIndex(index)
        else:
            # empty value
            cut_type_widget.setCurrentIndex(0)

        # a callback to update the property dict when the value changes
        def value_changed(new_value):
            properties["sg_cut_type"] = new_value

        # connect the widget index changed to the callback
        cut_type_widget.currentIndexChanged[str].connect(value_changed)

        # ---- construct the layout with a label

        cut_type_label = QtGui.QLabel("Cut Type:")
        cut_type_label.setToolTip(tooltip)

        cut_type_layout = QtGui.QHBoxLayout()
        cut_type_layout.addWidget(cut_type_label)
        cut_type_layout.addWidget(cut_type_widget)
        cut_type_layout.addStretch()

        return cut_type_layout

    def _build_tag_selector_widget(self, items, properties):
        """
        Returns a QT widget which contains the tag.
        """
        fields = ['code']
        filter = [['entity_type', 'is', 'Shot']]
        templates = [t['code'] for t in self.app.shotgun.find('TaskTemplate', filter, fields=fields)]

        schema = self.app.shotgun.schema_field_read('Shot', 'sg_status_list')
        statuses = schema['sg_status_list']['properties']['valid_values']['value']

        values = [statuses, templates]
        labels = ['Shotgun Shot Status', 'Shotgun Task Template for Shots']
        keys = ['sg_status_hiero_tags', 'task_template_map']

        # build a map of tag value pairs from the properties
        propertyDicts = [dict(properties[key]) for key in keys]
        propertyTags = list(set(itertools.chain(*[d.keys() for d in propertyDicts])))
        map = {}
        for tag in propertyTags:
            map[tag] = [d.get(tag, None) for d in propertyDicts]

        # add in blank entries for the current tags
        tags = self._get_tags(items)
        for tag in tags:
            map.setdefault(tag.name(), [None]*len(keys))

        # keep a known order
        names = sorted(map.keys())

        # setup the table
        tagTable = QtGui.QTableWidget(len(names), len(labels) + 1)
        tagTable.setMinimumHeight(150)
        tagTable.setHorizontalHeaderLabels(['Hiero Tags'] + labels)
        tagTable.setAlternatingRowColors(True)
        tagTable.setSelectionMode(tagTable.NoSelection)
        tagTable.setShowGrid(False)
        tagTable.verticalHeader().hide()
        tagTable.horizontalHeader().setStretchLastSection(True)
        tagTable.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)

        # on change rebuild the properties
        def changed(index):
            for (row, name) in enumerate(names):
                for (col, key) in enumerate(keys):
                    combo = tagTable.cellWidget(row, col+1)

                    # if no tag mapped to a name
                    if combo is None:
                        continue

                    # otherwise grab the text and keep it in the properties
                    select = combo.currentText()
                    propertyDicts[col][name] = (select and str(select) or None)
                    properties[key] = [(k, v) for (k, v) in propertyDicts[col].items() if v]

        # and build the table
        tagsByName = self._get_all_tags_by_name()
        for (row, name) in enumerate(names):
            tag = tagsByName.get(name, None)
            if tag is None:
                continue

            # build item for the tag
            item = QtGui.QTableWidgetItem(name)
            item.setIcon(QtGui.QIcon(tag.icon()))
            tagTable.setItem(row, 0, item)

            # build combo boxes for each set of values
            for (col, vals) in enumerate(values):
                combo = QtGui.QComboBox()
                combo.addItem(None)
                for (i, value) in enumerate(vals):
                    combo.addItem(value)
                    # see if the current item is the one in the properties
                    if map[name][col] == value:
                        combo.setCurrentIndex(i+1)
                combo.currentIndexChanged[int].connect(changed)
                # adjust sizes to avoid clipping or scrolling
                width = combo.minimumSizeHint().width()
                combo.setMinimumWidth(width)
                combo.setSizeAdjustPolicy(combo.AdjustToContents)
                tagTable.setCellWidget(row, col+1, combo)

        tagTable.resizeRowsToContents()
        tagTable.resizeColumnsToContents()

        width = sum([tagTable.columnWidth(i) for i in xrange(len(keys)+1)]) + 60
        tagTable.setMinimumWidth(width)

        return tagTable

    def _get_all_tags_by_name(self):
        """
        Returns all tags by name
        """
        tagsByName = {}
        projects = [hiero.core.project('Tag Presets')] + list(hiero.core.projects())
        for project in projects:
            tagsByName.update(dict([(tag.name(), tag) for tag in hiero.core.findProjectTags(project)]))
        return tagsByName

    def _get_tags(self, items):
        tags = FnExporterBase.tagsFromSelection(items, includeChildren=True)
        tags = [tag for (tag, objType) in tags if tag.visible() and "Transcode" not in tag.name()]
        tags = [tag for tag in tags if "Nuke Project File" not in tag.name()]
        return tags

class ShotgunShotProcessor(ShotgunHieroObjectBase, FnShotProcessor.ShotProcessor):
    """
    Adds hook functionality to the built in Shot processor.
    """
    def __init__(self, preset, submission=None, synchronous=False):
        FnShotProcessor.ShotProcessor.__init__(self, preset, submission, synchronous)

        # Call pre processor hook here to make sure it happens pior to any 'hook_resolve_custom_strings'.
        # The order if execution is basically [init processor, resolve user entries, startProcessing].
        self.app.execute_hook(
            "hook_pre_export",
            processor=self,
            base_class=HieroPreExport,
        )

    def startProcessing(self, exportItems, preview=False):
        """
        Executing the export
        """

        # In 10.5v1, the preview option was added. If True, then the export
        # dialog just needs a list of all the tasks that will run. Since we're
        # not adding tasks here, simply return the base class list.
        if self.app.get_nuke_version_tuple() >= (10, 5, 1) and preview:
            return FnShotProcessor.ShotProcessor.startProcessing(self, exportItems, preview)

        # add a top level task to manage shotgun shots
        exportTemplate = self._exportTemplate.flatten()
        properties = self._preset.properties().get('shotgunShotCreateProperties', {})

        # inject collate settings into Tasks where needed
        (collateTracks, collateShotNames) = self._getCollateProperties()
        for (itemPath, itemPreset) in exportTemplate:
            if 'collateTracks' in itemPreset.properties():
                itemPreset.properties()['collateTracks'] = collateTracks
            if 'collateShotNames' in itemPreset.properties():
                itemPreset.properties()['collateShotNames'] = collateShotNames

            # We need to pull any custom properties that were added to the
            # preset and get their current value, adding them to the item's
            # properties.
            custom_properties = self._get_custom_properties(
                get_method="get_shot_processor_ui_properties",
            )
            sg_shot_properties = self._preset.properties().get(
                "shotgunShotCreateProperties",
                dict(),
            )

            for property_data in custom_properties:
                key = property_data["name"]

                # If we don't have the current value for the property in the
                # shot processor preset, or the item's preset doesn't contain
                # the property, we move on without altering the item's properties.
                if key not in sg_shot_properties or key not in itemPreset.properties():
                    continue

                # Replace the default value that's in the item preset properties
                # right now with the current value from the shot processor preset,
                # which will reflect what the user set in the UI prior to exporting.
                itemPreset.properties()[key] = sg_shot_properties[key]

        exportTemplate.insert(0, (".shotgun", ShotgunShotUpdaterPreset(".shotgun", properties)))
        self._exportTemplate.restore(exportTemplate)

        # tag app as first shot
        self.app.shot_count = 0

        # need to temporarily monkey patch the internal hiero check so that our
        # preview quicktime is generated. See the notes in the method being
        # called for more info.
        self._override_frame_server_check()

        # startProcessing()'s signature changed in NukeStudio/Hiero 10.5v1.
        if self.app.get_nuke_version_tuple() >= (10, 5, 1):
            FnShotProcessor.ShotProcessor.startProcessing(self, exportItems, preview)
        else:
            FnShotProcessor.ShotProcessor.startProcessing(self, exportItems)

        # restore the monkey patched hiero method
        self._restore_frame_server_check()

        # get rid of our placeholder
        exportTemplate.pop(0)
        self._exportTemplate.restore(exportTemplate)

    def processTaskPreQueue(self):
        """Process the tasks just before they're queued up for execution."""

        # do the normal pre processing as defined in the base class
        FnShotProcessor.ShotProcessor.processTaskPreQueue(self)

        # if set, only exporting the cut portion of the source clip. If false,
        # the export will be the full clip
        cut_length = self._preset.properties()["cutLength"]

        # we'll keep a list of tuples of associated transcode and shot updater
        # tasks. later we'll attach cut related information to these tasks that
        # they can use during execution
        cut_related_tasks = []

        # iterate over the tasks groups to be executed
        for taskGroup in self._submission.children():

            # placeholders for the tasks we want to pre-process
            (shot_updater_task, transcode_task) = (None, None)

            # look at all the tasks in the group and identify the shot updater
            # and transcode tasks.
            for task in taskGroup.children():

                # shot updater
                if isinstance(task, ShotgunShotUpdater):
                    if task.isCollated():
                        # For collating sequences, skip tasks that are not hero
                        if task.isHero():
                            shot_updater_task = task
                    else:
                        # For non-collating sequences, add every task
                        shot_updater_task = task
                # transcode
                elif isinstance(task, ShotgunTranscodeExporter):
                    transcode_task = task

                if shot_updater_task:
                    # make the shot updater tasks aware of whether only the cut length
                    # portion of the source clip is being exported or the full clip
                    shot_updater_task._cut_length = cut_length

            # if there's not shot updater task, then we don't process. this is
            # likely due to collating and the task not being hero.
            if shot_updater_task:
                # add the associated tasks to the list of cut related tasks.
                # transcode_task may be None.
                cut_related_tasks.append((shot_updater_task, transcode_task))

        # sort the tasks based on their position in the timeline. this gives
        # us the cut order.
        cut_related_tasks.sort(key=lambda tasks: tasks[0]._item.timelineIn())

        # go ahead and populate the shot updater tasks with the cut order. this
        # is used to set the cut order on the Shot as it is created/updated.
        for i in range(0, len(cut_related_tasks)):
            (shot_updater_task, transcode_task) = cut_related_tasks[i]

            # Cut order is 1-based
            shot_updater_task._cut_order = i + 1

        # if you're wondering why we looped over the tasks above only to bail
        # out here if cuts support isn't available for the site, it's to
        # maintain backward compatibility for updating the Shot entities with
        # cut data which relies on setting `_cut_order` on those updater tasks.
        # The we also use the above loops to get the tasks in cut order which
        # will be used in `_processCuts` if the site has cut support.

        if not self._cutsSupported():
            # cuts not supported. all done here
            self.app.log_info(
                "No Cut support in this version of Shotgun. Not attempting to "
                "create Cut or CutItem entries."
            )
            return

        # We give the hook method the opportunity to determine whether we'll
        # continue with updating the Cut entity. Passing in the shot creation
        # properties from the preset will allow programmers to customize this
        # behavior based on any custom properties they've added to the preset
        # through the customize_export_ui hook methods.
        allow_cut_updates = self.app.execute_hook_method(
            "hook_update_cuts",
            "allow_cut_updates",
            preset_properties=self._preset.properties().get(
                "shotgunShotCreateProperties",
                dict(),
            ),
            base_class=HieroUpdateCuts,
        )

        if not allow_cut_updates:
            return

        # collate complicates cut support for hiero. For now duck out at this
        # point with a log msg. The user should be aware of this from the
        # message in the collating preset UI.
        (collateTracks, collateShotNames) = self._getCollateProperties()
        if collateTracks or collateShotNames:
            self.app.log_info(
                "Cut support is ill defined for collating in Hiero. Not "
                "attempting to create Cut or CutItem entries in Shotgun."
            )
            return

        # ---- at this point, we have the cut related tasks in order.

        self.app.engine.show_busy(
            "Preprocessing Sequence",
            "Creating Cut in Shotgun ..."
        )

        # wrap in a try/catch to make sure we can clear the popup at the end
        try:
            # pre-process the cut data for the tasks about to execute
            self._processCut(cut_related_tasks)
        finally:
            self.app.engine.clear_busy()

    def _getCollateProperties(self):
        """
        Returns tuple with values for collateTracks collateShotNames settings.
        """

        properties = self._preset.properties().get("shotgunShotCreateProperties", {})

        collateTracks = properties.get("collateTracks", False)
        collateShotNames = properties.get("collateShotNames", False)

        return (collateTracks, collateShotNames)

    def _getCutData(self, hiero_sequence):
        """
        Returns a dict of cut data for the supplied hiero sequence.

        :param hiero_sequence: `hiero.core.Sequence` object
        :return: dict - cut data fields
        """

        parent_entity = None

        try:
            # get the parent entity in SG that corresponds to the hiero sequence
            parent_entity = self.app.execute_hook_method(
                "hook_get_shot",
                "get_shot_parent",
                hiero_sequence=hiero_sequence,
                data=self.app.preprocess_data,
                upload_thumbnail=False,
                base_class=HieroGetShot,
            )
        except TankHookMethodDoesNotExistError, e:
            # the method doesen't exist in the hook. the hook may have been
            # overridden previously and not updated to include this method.
            # this will imply a Cut stream without a parent entity. For now,
            # we will log a warning and continue.
            self.app.log_warning(
                "The method 'get_shot_parent' could not be found in the "
                "'hook_get_shot' hook. In order to properly link the "
                "Cut entity in SG, you will need to implement this method "
                "to return a Sequence, Episode, or some other entity "
                "that corresponds to the Hiero sequence in your workflow."
            )
            pass

        # determine which revision number of the cut to create. look for an
        # existing Cut with the sequence name with the same parent.
        sg = self.app.shotgun
        prev_cut = sg.find_one(
            "Cut",
            [["code", "is", hiero_sequence.name()],
             ["entity", "is", parent_entity]],
            ["revision_number"],
            [{"field_name": "revision_number", "direction": "desc"}]
        )

        if prev_cut is None:
            # no matching Cut, start out at version 1
            next_revision_number = 1
        else:
            # match! use the next revision number
            next_revision_number = prev_cut["revision_number"] + 1

        self._app.log_debug(
            "The cut revision number will be %s." % (next_revision_number,))

        # retrieve the cut type from the processor presets
        properties = self._preset.properties().get(
            "shotgunShotCreateProperties", {})
        cut_type = properties.get("sg_cut_type", "")

        # the bulk of the cut data. the rest will be populated as the individual
        # shots are processed in the cut
        return  {
            "project": self.app.context.project,
            "entity": parent_entity,
            "code": hiero_sequence.name(),
            "sg_cut_type": cut_type,
            "description": "",
            "revision_number": next_revision_number,
            "fps": hiero_sequence.framerate().toFloat(),
        }

    def _override_frame_server_check(self):
        """
        This method temporarily monkey patches the hiero method that checks
        whether or not the frame server is running.

        We monkey patch this to allow our preview quicktimes created in the
        transcode task to continue to be uploaded when doing individual frame
        exports. In previous versions of Hiero, the .nk script was always
        executed as a LocalNukeRenderTask. As of Hiero 10, a new task type is
        used for frame exports called FrameServerRenderTask. This task type
        renders frames in an individual frame context within Nuke and therefore
        our quicktime write node never runs. Thus no quicktime upload for the
        SG Version and no thumbnail.

        By overriding this method and forcing a value of ``False``, we trick
        the Hiero shot processor internals into thinking that there is no frame
        server running and cause it to use the fallback LocalNukeRenderTask
        which does what we need.

        This fix is a work around and given time we might consider a better
        solution. That might include separating the preview quicktime
        generation into a separate .nk script and transcode task.
        """

        try:
            # import the module containing the method to override
            import hiero.ui.nuke_bridge.FnNsFrameServer

            # keep a handle on the real method
            self._real_frame_server_check = hiero.ui.nuke_bridge.FnNsFrameServer.isServerRunning

            # override the real method to always return False. i.e. The frame
            # server is not running.
            hiero.ui.nuke_bridge.FnNsFrameServer.isServerRunning = lambda t=1: False
        except Exception, e:
            # log a debug message in case something happens.
            self._app.log_debug(
                "Unable to override the frame server check. If exporting individual "
                "frames, this may prevent the upload of a quicktime to SG."
            )

    def _restore_frame_server_check(self):
        """
        Restoring the original method monkey patched in the method above.

        See the notes there for more details.
        """

        try:
            import hiero.ui.nuke_bridge.FnNsFrameServer
            real_fs_check = self._real_frame_server_check

            # restore the real method
            hiero.ui.nuke_bridge.FnNsFrameServer.isServerRunning = real_fs_check
        except Exception, e:
            # unable to restore. likely associated with a failure to monkey
            # patch. no need to log another message.
            pass

    def _processCut(self, cut_related_tasks):
        """Collect data and create the Cut and CutItem entries for the tasks.

        We need to pre-create the Cut entity so that the CutItems can be
        parented to it.

        :param cut_related_tasks: A sorted list of tuples of the form:
            (shot_updater_task, transcode_task)
        """

        # make sure the data cache is ready. this code may create entities in
        # SG and they'll be stored here for reuse.
        if not hasattr(self.app, "preprocess_data"):
            self.app.preprocess_data = {}

        # get the hiero sequence from the first updater task's item. this would
        # be the first item in the first tuple of the list of cut related tasks.
        hiero_sequence = cut_related_tasks[0][0]._item.sequence()

        # the sequence fps, used to calculate timecodes for cut items
        fps = hiero_sequence.framerate().toFloat()

        # get whether sequence timecode is displayed in drop frame format
        drop_frame = hiero_sequence.dropFrame()

        # go ahead populate the bulk of the cut data. the first and last
        # cut items will populate the cut's in/out points.
        cut_data = self._getCutData(hiero_sequence)

        # we'll also calculate the cut duration while processing the tasks
        cut_duration = 0

        # list of cut item data
        cut_item_data_list = []

        # process the tasks in order
        for (shot_updater_task, transcode_task) in cut_related_tasks:

            # cut order was populated by the calling method to update the
            # Shot entity's cut info
            cut_order = shot_updater_task._cut_order

            # this retrieves the basic cut information from the updater task.
            # cut item in/out, cut item duration, edit in/out.
            cut_item_data = shot_updater_task.get_cut_item_data()

            # clean out the unnecessary fields used by the shot updater
            for field in ["edit_duration", "head_in", "tail_out", "working_duration"]:
                del cut_item_data[field]

            # add the length of this item to the full cut duration
            cut_duration += cut_item_data["cut_item_duration"]

            # translate some of the cut item data into timecodes that will also
            # be populated in the cut item
            tc_cut_item_in = self._timecode(cut_item_data["cut_item_in"], fps, drop_frame)
            tc_cut_item_out = self._timecode(cut_item_data["cut_item_out"], fps, drop_frame)
            tc_edit_in = self._timecode(cut_item_data["edit_in"], fps, drop_frame)
            tc_edit_out = self._timecode(cut_item_data["edit_out"], fps, drop_frame)

            # get the shot so that we have all we need for the cut item.
            # this may create the shot if it doesn't exist already
            shot = self.app.execute_hook(
                "hook_get_shot",
                task=shot_updater_task,
                item=shot_updater_task._item,
                data=self.app.preprocess_data,
                upload_thumbnail=False,
                base_class=HieroGetShot,
            )

            # update the cut item data with the shot, timecodes and other fields
            # required
            cut_item_data.update({
                "code": shot_updater_task.clipName(),
                "project": self.app.context.project,
                "shot": {"id": shot["id"], "type": "Shot"},
                "cut_order": cut_order,
                "timecode_cut_item_in_text": tc_cut_item_in,
                "timecode_cut_item_out_text": tc_cut_item_out,
                "timecode_edit_in_text": tc_edit_in,
                "timecode_edit_out_text": tc_edit_out,
            })

            # add the cut item data to each of the cut related tasks. they
            # will be responsible for ensuring the cut item exists and updating
            # any additional information
            shot_updater_task._cut_item_data = cut_item_data

            # dont' want to assume that there is an associated transcode task.
            # if there is, attach the cut item data so that the version is
            # updated. If not, then we'll get a cut item without an associated
            # version (cut info only in SG, nothing playable).
            if transcode_task:
                transcode_task._cut_item_data = cut_item_data

            if cut_order == 1:
                # first item in the cut, set the cut's start timecode
                cut_data["timecode_start_text"] = tc_edit_in

                # let the first shot_updater be responsible for uploading
                # a thumbnail for the Cut
                shot_updater_task._create_cut_thumbnail = True

            if cut_order == len(cut_related_tasks):
                # last item in the cut, set the cut's end timecode
                cut_data["timecode_end_text"] = tc_edit_out

            cut_item_data_list.append(cut_item_data)

        # all tasks processed, add the duration to the cut data
        cut_data["duration"] = cut_duration

        # create the cut to get the id.
        sg = self.app.shotgun
        cut = sg.create("Cut", cut_data)
        self._app.log_debug("Created Cut in Shotgun: %s" % (cut,))
        self._app.log_info("Created Cut '%s' in Shotgun!" % (cut["code"],))

        # make sure the cut item data dicts are updated with the cut info
        for cut_item_data in cut_item_data_list:
            cut_item_data["cut"] = {"id": cut["id"], "type": "Cut"}

    def _timecode(self, frame, fps, drop_frame=False):
        """Convenience wrapper to convert a given frame and fps to a timecode.

        :param frame: Frame number
        :param fps: Frames per seconds (float)
        :return: timecode string
        """

        if drop_frame:
            display_type = hiero.core.Timecode.kDisplayDropFrameTimecode
        else:
            display_type = hiero.core.Timecode.kDisplayTimecode

        return hiero.core.Timecode.timeToString(frame, fps, display_type)


class ShotgunShotProcessorPreset(ShotgunHieroObjectBase, FnShotProcessor.ShotProcessorPreset, CollatedShotPreset):
    """
    Handles presets for the shot processor.
    """
    def __init__(self, name, properties):
        FnShotProcessor.ShotProcessorPreset.__init__(self, name, properties)

        self._parentType = ShotgunShotProcessor

        # set up default properties
        self.properties()['shotgunShotCreateProperties'] = {}
        default_properties = self.properties()['shotgunShotCreateProperties']
        CollatedShotPreset.__init__(self, default_properties)

        # add setting to control how we map sg statuses and tags
        # just map the standard "status" tags in hiero against
        # the standard task statuses in Shotgun. If a user wants
        # to change these, they can just create a new preset :)
        default_properties["sg_status_hiero_tags"] = [ ("Ready To Start", "rdy"),
                                                       ("In Progress", "ip"),
                                                       ("On Hold", "hld"),
                                                       ("Final", "fin"), ]

        # add setting to control the default task template in Shotgun.
        # again, populate some of the standard tags in hiero. The rest
        # of them can be manually set.
        default_template = self.app.get_setting('default_task_template')
        default_properties["task_template_map"] = [("Ready To Start", default_template),
                                                   ("In Progress", default_template),
                                                   ("On Hold", default_template),
                                                   ("Final", default_template)]

        # holds the cut type to use when creating Cut entires in SG
        default_properties["sg_cut_type"] = ""

        # Handle custom properties from the customize_export_ui hook.
        custom_properties = self._get_custom_properties(
            "get_shot_processor_ui_properties"
        ) or []

        default_properties.update({d["name"]: d["value"] for d in custom_properties})

        # finally, update the properties based on the properties passed to the constructor
        explicit_constructor_properties = properties.get('shotgunShotCreateProperties', {})
        default_properties.update(explicit_constructor_properties)

    def addUserResolveEntries(self, resolver):
        self.app.log_debug('Adding custom resolver tk_version')

        # the following hook can end up pulling shots from the get_shot hook,
        # so initialize the cache that is used to store the values from that
        # hook.
        if not hasattr(self.app, "preprocess_data"):
            self.app.preprocess_data = {}

        resolver.addResolver("{tk_version}", "Version string formatted by Shotgun Toolkit.", 
                             lambda keyword, task: self._formatTkVersionString(task.versionString()))

        custom_template_fields = self.app.get_setting("custom_template_fields")
        self.app.log_debug('Adding custom resolvers %s' % [ctf['keyword'] for ctf in custom_template_fields])
        for ctf in custom_template_fields:
            resolver.addResolver(
                "{%s}" % ctf['keyword'], ctf['description'],
                lambda keyword, task:
                    self.app.execute_hook(
                        "hook_resolve_custom_strings",
                        keyword=keyword,
                        task=task,
                        base_class=HieroResolveCustomStrings,
                    )
            )

    def isValid(self):
        """
        This method was introduced into the base class in NukeStudio/Hiero
        10.5v1. The base class implementation requires each exporter have at
        least one write node. Returning the True value expected allows
        our exports to continue since we populate the write node automatically
        during the export.
        """
        return (True, "")

