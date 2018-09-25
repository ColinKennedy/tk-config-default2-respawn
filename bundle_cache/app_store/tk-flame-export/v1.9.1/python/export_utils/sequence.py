# Copyright (c) 2016 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import pprint
from .shot import Shot
from sgtk import TankError
import sgtk


class Sequence(object):
    """
    Class representing a sequence in Shotgun/Flame
    """

    def __init__(self, name):
        """
        Constructor

        :param name: Sequence name
        """
        self._name = name
        self._shotgun_id = None
        self._shots = {}

        self._app = sgtk.platform.current_bundle()

        # get some app settings configuring how shots are parented
        self._shot_parent_entity_type = self._app.get_setting("shot_parent_entity_type")
        self._shot_parent_link_field = self._app.get_setting("shot_parent_link_field")

    def __repr__(self):
        return "<Sequence %s %s>" % (self._shot_parent_entity_type, self._name)

    @property
    def name(self):
        """
        Returns the name of the sequence
        """
        return self._name

    @property
    def shotgun_id(self):
        """
        Returns shotgun id for this sequence
        """
        return self._shotgun_id

    @property
    def shots(self):
        """
        Shots associated with this sequence
        """
        return self._shots.values()

    @property
    def shots_with_segments(self):
        """
        Non-empty shots associated with this sequence

        Note: there may be shots present without a segment due
        to a user cancelling parts of the export during the process
        - for example, flame may prompt whether a user wants to override
        an existing sequence or not, resulting in shots with no segments.

        This property ensures that all shots returned contain segments
        and thus aren't just "empty wrappers" but contain cut data.
        """
        return [shot for shot in self.shots if len(shot.segments) > 0]


    def add_shot(self, shot_name):
        """
        Adds a shot to this sequence.

        :param shot_name: Shot name
        :returns: The constructed Shot object
        """
        self._shots[shot_name] = Shot(self, shot_name)
        return self._shots[shot_name]

    def get_shot(self, shot_name):
        """
        Returns a shot object given its name

        :param shot_name: name of shot to retrieve
        :returns: Shot object
        """
        if shot_name not in self._shots:
            raise ValueError("Cannot find shot %s in %s" % (shot_name, self))

        return self._shots[shot_name]

    def process_shotgun_shot_structure(self):
        """
        Processes and populates Shotgun and filesystem data.

        - Ensures that the sequence exists in Shotgun
        - Ensures that the shots exist in Shotgun
        - Populates Shotgun data for Sequence and Shot objects
        - Creates folders on disk for any new objects
        - Computes the context for all shot objects
        """
        self._app.log_debug("Preparing export structure for %s %s and shots %s" % (
            self._shot_parent_entity_type,
            self._name,
            self._shots.keys())
        )

        self._app.engine.show_busy("Preparing Shotgun...", "Preparing Shots for export...")

        try:
            # find and create shots and sequence in Shotgun
            self._ensure_sg_shot_structure()

            # now get a list of all new shots
            new_shots = [shot for shot in self._shots.values() if shot.new_in_shotgun]

            # run folder creation for our newly created shots
            self._app.log_debug("Creating folders on for all new shots...")
            for (idx, shot) in enumerate(new_shots):
                # this is a new shot
                msg = "Step %s/%s: Creating folders for Shot %s..." % (idx+1, len(new_shots), shot.name)
                self._app.engine.show_busy("Preparing Shotgun...", msg)
                self._app.log_debug("Creating folders on disk for Shot id %s..." % shot)
                self._app.sgtk.create_filesystem_structure(
                    "Shot",
                    shot.shotgun_id,
                    engine="tk-flame"
                )
                self._app.log_debug("...folder creation complete")

            # establish a context for all objects
            self._app.engine.show_busy("Preparing Shotgun...", "Resolving Shot contexts...")
            self._app.log_debug("Caching contexts...")
            for shot in self._shots.values():
                shot.cache_context()

        finally:
            # kill progress indicator
            self._app.engine.clear_busy()

    def compute_shot_cut_changes(self):
        """
        Compute the difference between flame cut data
        and the registered shot data in Shotgun.

        process_shotgun_shot_structure() needs to be executed before
        this method can be executed.

        :returns: A list of shotgun batch updates required
                  in order for Shotgun to be up to date with
                  Flame.
        """
        self._app.log_debug("Computing cut changes between Shotgun and Flame....")

        shotgun_batch_items = []

        # now sort in order
        shots_in_cut_order = sorted(
            self.shots_with_segments,
            key=lambda x: x.get_base_segment().edit_in_frame
        )

        for index, shot in enumerate(shots_in_cut_order):
            # make cut order 1 based
            cut_order = index + 1
            # get full cut data
            (sg_in, sg_out, sg_cut_order) = shot.get_sg_shot_in_out()

            # we get the edit points in flame from the base layer
            base_seg = shot.get_base_segment()

            if base_seg.cut_in_frame != sg_in or base_seg.cut_out_frame != sg_out or cut_order != sg_cut_order:

                # note that at this point all shots are guaranteed to exist in Shotgun
                # since they were created in the initial export step.
                sg_cut_batch = {
                    "request_type": "update",
                    "entity_type": "Shot",
                    "entity_id": shot.shotgun_id,
                    "data": {
                        "sg_cut_in": base_seg.cut_in_frame,
                        "sg_cut_out": base_seg.cut_out_frame,
                        "sg_head_in": base_seg.head_in_frame,
                        "sg_tail_out": base_seg.tail_out_frame,
                        "sg_cut_duration": base_seg.duration,
                        "sg_cut_order": cut_order
                    }
                }

                self._app.log_debug("Registering cut change: %s" % pprint.pformat(sg_cut_batch))
                shotgun_batch_items.append(sg_cut_batch)

        return shotgun_batch_items

    def create_cut(self, cut_type):
        """
        Creates a cut with corresponding cut items in Shotgun.

        Checks if any existing cut exists and in that case computes
        the highest revision number available and creates a cut with
        one version higher.

        Before this can be executed, process_shotgun_shot_structure()
        must have been executed and version ids must have been assigned to
        all Segment objects.

        :param cut_type: Type of the cut to create. None or "" for no cut type.
        """
        # minimum shotgun version that supports new cut schema
        MIN_CUT_SG_VERSION = (7, 0, 0)

        sg = self._app.shotgun

        if sg.server_caps.version < MIN_CUT_SG_VERSION:
            self._app.log_debug(
                "Shotgun site does not support cuts. Will not update cut information."
            )
            return

        self._app.engine.show_busy("Updating Shotgun...", "Creating Cut...")

        try:

            parent_entity_link = {
                "id": self.shotgun_id,
                "type": self._shot_parent_entity_type
            }

            # first determine which revision number of the cut to create
            prev_cut = sg.find_one(
                "Cut",
                [["code", "is", self.name],
                 ["entity", "is", parent_entity_link]],
                ["revision_number"],
                [{"field_name": "revision_number", "direction": "desc"}]
            )
            if prev_cut is None:
                next_revision_number = 1
            else:
                next_revision_number = prev_cut["revision_number"] + 1

            self._app.log_debug("The cut revision number will be %s." % next_revision_number)

            # get the shots in cut order
            shots_in_cut_order = sorted(
                self.shots_with_segments,
                key=lambda x: x.get_base_segment().edit_in_frame
            )

            # first create a new cut
            sg_cut = sg.create(
                "Cut",
                {
                    "project": self._app.context.project,
                    "entity": parent_entity_link,
                    "code": self.name,
                    "sg_cut_type": cut_type,
                    "description": "Automatically created by the Flame Shot exporter.",
                    "revision_number": next_revision_number,
                    # get the fps for the entire sequence by pulling it from
                    # the first segment
                    "fps": shots_in_cut_order[0].get_base_segment().sequence_fps,
                    "duration": sum([shot.get_base_segment().duration for shot in self.shots if shot.get_base_segment() is not None]),
                    "timecode_start_text": shots_in_cut_order[0].get_base_segment().edit_in_timecode,
                    "timecode_end_text": shots_in_cut_order[-1].get_base_segment().edit_out_timecode,
                }
            )

            # now create the cut items in a single batch call
            sg_batch_data = []
            for index, shot in enumerate(shots_in_cut_order):
                # make cut order 1 based
                cut_order = index + 1
                # we are pulling most values from the base layer
                segment = shot.get_base_segment()

                version_link = None
                if segment.has_shotgun_version:
                    version_link = {"id": segment.shotgun_version_id, "type": "Version"}

                batch = {
                    "request_type": "create",
                    "entity_type": "CutItem",
                    "data": {
                        "code": segment.name,
                        "project": self._app.context.project,
                        "shot": {"id": shot.shotgun_id, "type": "Shot"},
                        "cut": {"id": sg_cut["id"], "type": sg_cut["type"]},
                        "version": version_link,
                        "cut_item_in": segment.cut_in_frame,
                        "cut_item_out": segment.cut_out_frame,
                        "edit_in": segment.edit_in_frame,
                        "edit_out": segment.edit_out_frame,
                        "cut_order": cut_order,
                        "timecode_cut_item_in_text": segment.cut_in_timecode,
                        "timecode_cut_item_out_text": segment.cut_out_timecode,
                        "timecode_edit_in_text": segment.edit_in_timecode,
                        "timecode_edit_out_text": segment.edit_out_timecode
                    }
                }

                sg_batch_data.append(batch)

            self._app.log_debug("Executing sg batch command for cut items....")
            sg.batch(sg_batch_data)
            self._app.log_debug("...done!")

        finally:
            # turn off UI prompt
            self._app.engine.clear_busy()

    def _ensure_sg_shot_structure(self):
        """
        Ensures that Shots and sequences exist in Shotgun.

        Will automatically create Shots and Sequences if necessary
        and assign task templates.

        Shotgun Shot and Sequence data for objects will be populated.
        """
        self._app.log_debug("Ensuring sequence and shots exists in Shotgun...")
        # get some configuration settings first
        shot_task_template = self._app.get_setting("task_template")
        if shot_task_template == "":
            shot_task_template = None

        parent_task_template = self._app.get_setting("shot_parent_task_template")
        if parent_task_template == "":
            parent_task_template = None

        # handy shorthand
        project = self._app.context.project

        # Ensure that a parent exists in Shotgun with the parent name
        self._app.engine.show_busy(
            "Preparing Shotgun...",
            "Locating %s %s..." % (self._shot_parent_entity_type, self.name)
        )

        self._app.log_debug("Locating Shot parent object in Shotgun...")
        sg_parent = self._app.shotgun.find_one(
            self._shot_parent_entity_type,
            [["code", "is", self.name], ["project", "is", project]]
        )

        if sg_parent:
            self._app.log_debug("Parent %s already exists in Shotgun." % sg_parent)
            self._shotgun_id = sg_parent["id"]

        else:
            # Create a new parent object in Shotgun

            # First see if we should assign a task template
            if parent_task_template:
                # resolve task template
                self._app.engine.show_busy("Preparing Shotgun...", "Loading task template...")
                sg_task_template = self._app.shotgun.find_one(
                    "TaskTemplate",
                    [["code", "is", parent_task_template]]
                )
                if not sg_task_template:
                    raise TankError(
                        "The task template '%s' does not exist in Shotgun!" % parent_task_template
                    )
            else:
                sg_task_template = None

            self._app.engine.show_busy(
                "Preparing Shotgun...",
                "Creating %s %s..." % (self._shot_parent_entity_type, self.name)
            )

            sg_parent = self._app.shotgun.create(
                self._shot_parent_entity_type,
                {"code": self.name,
                 "task_template": sg_task_template,
                 "description": "Created by the Shotgun Flame exporter.",
                 "project": project}
            )
            self._shotgun_id = sg_parent["id"]
            self._app.log_debug("Created parent %s" % sg_parent)


        # Locate a task template for shots
        if shot_task_template:
            # resolve task template
            self._app.engine.show_busy("Preparing Shotgun...", "Loading task template...")
            sg_task_template = self._app.shotgun.find_one(
                "TaskTemplate",
                [["code", "is", shot_task_template]]
            )
            if not sg_task_template:
                raise TankError(
                    "The task template '%s' does not exist in Shotgun!" % shot_task_template
                )
        else:
            sg_task_template = None

        # now attempt to retrieve metadata for all shots. Shots that are not found are created.
        self._app.engine.show_busy("Preparing Shotgun...", "Loading Shot data...")

        self._app.log_debug("Loading shots from Shotgun...")

        shot_parent_link = {"id": self._shotgun_id, "type": self._shot_parent_entity_type}

        # get list of shots as strings
        shot_names = self._shots.keys()

        # find them in shotgun
        sg_shots = self._app.shotgun.find(
            "Shot",
            [["code", "in", shot_names],
             [self._shot_parent_link_field, "is", shot_parent_link]],
            ["code", "sg_cut_in", "sg_cut_out", "sg_cut_order"]
        )
        self._app.log_debug("...got %s shots." % len(sg_shots))

        # add sg data to shot objects
        for sg_shot in sg_shots:
            shot_name = sg_shot["code"]
            self._shots[shot_name].set_sg_data(sg_shot, False)

        # create all shots that don't already exist
        sg_batch_data = []
        for shot in self._shots.values():
            if not shot.exists_in_shotgun:
                # this shot does not yet exist in Shotgun
                batch = {
                    "request_type": "create",
                    "entity_type": "Shot",
                    "data": {
                        "code": shot.name,
                        "description": "Created by the Shotgun Flame exporter.",
                        self._shot_parent_link_field: shot_parent_link,
                        "task_template": sg_task_template,
                        "project": project
                    }
                }
                self._app.log_debug("Adding to Shotgun batch queue: %s" % batch)
                sg_batch_data.append(batch)

        if len(sg_batch_data) > 0:
            self._app.engine.show_busy("Preparing Shotgun...", "Creating new shots...")

            self._app.log_debug("Executing sg batch command....")
            sg_batch_response = self._app.shotgun.batch(sg_batch_data)
            self._app.log_debug("...done!")

            # register its data with Shot objects
            for sg_data in sg_batch_response:
                shot_name = sg_data["code"]
                self._shots[shot_name].set_sg_data(sg_data, True)


