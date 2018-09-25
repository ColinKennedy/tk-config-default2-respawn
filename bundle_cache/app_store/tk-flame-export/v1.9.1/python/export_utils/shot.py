# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sgtk
from sgtk import TankError

from .segment import Segment

class Shot(object):
    """
    Represents a Shot in Flame and Shotgun.
    """

    def __init__(self, parent, name):
        """
        Constructor

        :param name: Name of the Shot
        """
        # set up the basic properties of this value wrapper
        self._app = sgtk.platform.current_bundle()

        self._name = name
        self._parent = parent
        self._created_this_session = False
        self._context = None
        self._shotgun_id = None
        self._sg_cut_in = None
        self._sg_cut_out = None
        self._sg_cut_order = None
        self._flame_batch_data = None
        self._segments = {}

    def __repr__(self):
        return "<Shot %s, %s>" % (self._name, self._parent)

    @property
    def new_in_shotgun(self):
        """
        True if this object was created in Shotgun as part of this session.
        """
        return self._created_this_session

    @property
    def name(self):
        """
        Returns the name of the shot
        """
        return self._name

    @property
    def context(self):
        """
        Returns the context associated with this shot
        """
        return self._context

    @property
    def shotgun_id(self):
        """
        Shotgun id for this Shot
        """
        return self._shotgun_id

    @property
    def segments(self):
        """
        List of segment objects for this shot
        """
        return self._segments.values()

    @property
    def exists_in_shotgun(self):
        """
        Returns true if the shot has an associated shotgun id
        """
        return self._shotgun_id is not None

    @property
    def has_batch_export(self):
        """
        Returns true if a batch export is associated with this shot, false if not.

        It is possible that an export doesn't have a batch file exported if Flame for example
        prompts the user, asking her/him if they want to override an existing file and they
        select 'no'
        """
        return self._flame_batch_data is not None

    @property
    def batch_path(self):
        """
        Return the flame batch export path for this shot
        """
        if not self.has_batch_export:
            raise TankError("Cannot get batch path - no batch metadata found!")

        return os.path.join(
            self._flame_batch_data.get("destinationPath"),
            self._flame_batch_data.get("resolvedPath")
        )

    @property
    def batch_version_number(self):
        """
        Return the version number associated with the batch file
        """
        if not self.has_batch_export:
            raise TankError("Cannot get batch path - no batch metadata found!")

        return int(self._flame_batch_data["versionNumber"])

    def get_base_segment(self):
        """
        Returns the base segment for this shot.

        The base segment is the segment that is located lowest down in the stack
        and it is this segment that is used to determine the cut information for the Shot.

        The logic for picking the base segment is simple and may need adjustment
        in the future; right now it looks at the list of segments for the Shot
        and chooses the one with the lowest track id.

        Shots without segments may return None. This is an edge case which may
        happen if for example Flame prompts a user "do you want to overwrite an
        existing render", and the user responds with No.

        :returns: Segment object or None if not defined
        """
        if len(self._segments) == 0:
            return None

        return min(
            self._segments.values(),
            key=lambda segment: segment.flame_track_id
        )

    def get_sg_shot_in_out(self):
        """
        Returns shotgun cut data.

        Returns values based on the base segment, e.g. the segment
        found lowest in the stack. Returns both existing sg values
        from the Shot entity and values from Flame.

        Returns a tuple with the following items:

        (sg_shot_in, sg_shot_out, sg_cut_order)

        The return data is in frames, computed relative to the sequence
        level time code in Flame.

        :return: see above
        """
        cut_data = (
            self._sg_cut_in,
            self._sg_cut_out,
            self._sg_cut_order
        )
        return cut_data

    def set_sg_data(self, sg_data, new_in_shotgun):
        """
        Set shotgun data associated with this shot.

        The input shotgun data dict needs to contain at least
        the following keys: id, sg_cut_in, sg_cut_out, sg_cut_order

        :param sg_data: Shotgun dictionary with
        :param new_in_shotgun: Boolean to indicate if this shot was just created.
        """
        self._created_this_session = new_in_shotgun
        self._shotgun_id = sg_data["id"]
        # note - for new shots, the sg_cut_in key may not be part of sg_data
        self._sg_cut_in = sg_data.get("sg_cut_in")
        self._sg_cut_out = sg_data.get("sg_cut_out")
        self._sg_cut_order = sg_data.get("sg_cut_order")

    def cache_context(self):
        """
        Computes the context for this Shot and caches it locally.
        """
        self._app.log_debug("Caching context for %s" % self)
        self._context = self._app.sgtk.context_from_entity("Shot", self.shotgun_id)

    def add_segment(self, segment_name):
        """
        Adds a segment to this Shot.

        :param segment_name: Name of segment to add
        :returns: Segment object
        """
        segment = Segment(self, segment_name)
        self._segments[segment_name] = segment
        return segment

    def set_flame_batch_data(self, data):
        """
        Specify the flame hook data dictionary for this shot

        :param data: dictionary with data from flame
        """
        self._flame_batch_data = data

