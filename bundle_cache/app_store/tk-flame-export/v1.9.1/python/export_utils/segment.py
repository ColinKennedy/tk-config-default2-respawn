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


class Segment(object):
    """
    Represents a timeline segment in flame.

    Each timeline segment is parented under a shot.

    Details on Flame's data sent thru the exported hooks can be found at
    https://knowledge.autodesk.com/search-result/caas/CloudHelp/cloudhelp/2017/ENU/Flame-API/files/GUID-8EE47B4F-16F0-41D6-97BB-1226C0BDCC45-htm.html
    """
    def __init__(self, parent, name):
        """
        Constructor
        """
        self._app = sgtk.platform.current_bundle()

        self._shot = parent
        self._name = name
        self._flame_data = None

        # associated shotgun version
        self._shotgun_version_id = None

    def __repr__(self):
        return "<Segment %s, %s>" % (self._name, self._shot)

    @property
    def shot(self):
        """
        Returns the shot that this segment belongs to
        """
        return self._shot

    @property
    def name(self):
        """
        Returns the name of the segment
        """
        return self._name

    @property
    def has_shotgun_version(self):
        """
        Returns true if a Shotgun version exists for the render associated with this segment.
        If a Shotgun version exists, it is implied that a render also exists.
        """
        return self._shotgun_version_id is not None

    @property
    def shotgun_version_id(self):
        """
        Returns the Shotgun id for the version associated with this segment, if there is one.
        """
        if not self.has_shotgun_version:
            raise TankError("Cannot get Shotgun version id for segment - no version associated!")
        return self._shotgun_version_id

    @property
    def has_render_export(self):
        """
        Returns true if a render export is associated with this segment, false if not.

        It is possible that an export doesn't have a render file exported if Flame for example
        prompts the user, asking her/him if they want to override an existing file and they
        select 'no'
        """
        return self.flame_data is not None

    @property
    def render_version_number(self):
        """
        Return the version number associated with the render file
        """
        return int(self._get_flame_property("versionNumber"))

    @property
    def render_path(self):
        """
        Return the export render path for this segment
        """
        return os.path.join(
            self._get_flame_property("destinationPath"),
            self._get_flame_property("resolvedPath")
        )

    @property
    def render_aspect_ratio(self):
        """
        Return the aspect ratio associated with the render file
        """
        return self._get_flame_property("aspectRatio")

    @property
    def backburner_job_id(self):
        """
        Return the backburner job id associated with this segment or None if not defined.
        """
        backburner_id = None
        if self._get_flame_property("isBackground"):
            backburner_id = self._get_flame_property("backgroundJobId")
        return backburner_id

    @property
    def render_width(self):
        """
        Returns the width of the flame render
        """
        return self._get_flame_property("width")

    @property
    def fps(self):
        """
        Returns the fps of this segment
        """
        # fps is passed as a string by flame
        return float(self._get_flame_property("fps"))

    @property
    def use_drop_frames(self):
        """
        Returns true if the FPS setting is using dropped frames
        """
        # fps is passed as a string by flame
        return self._get_flame_property("drop")

    @property
    def sequence_fps(self):
        """
        Returns the fps of the sequence that this segment belongs to
        """
        # fps is passed as a string by flame
        return float(self._get_flame_property("sequenceFps"))

    @property
    def sequence_use_drop_frames(self):
        """
        Returns true if the sequence FPS setting is using dropped frames
        """
        # fps is passed as a string by flame
        return self._get_flame_property("sequenceDrop")

    @property
    def render_height(self):
        """
        Returns the height of the flame render
        """
        return self._get_flame_property("height")

    @property
    def flame_track_id(self):
        """
        Returns the track id in flame, as an int
        """
        # flame stores track id as a three zero padded str, e.g. "002"
        return int(self._get_flame_property("track"))

    @property
    def duration(self):
        """
        Returns the duration of this segment
        """
        return self.edit_out_frame - self.edit_in_frame + 1

    @property
    def edit_in_frame(self):
        """
        Returns the in frame timecode for the edit point
        This denotes where this segment sits in the sequence based timeline.
        """
        return self._get_flame_property("recordIn")

    @property
    def edit_out_frame(self):
        """
        Returns the out frame timcode for the edit point.
        This denotes where this segment sits in the sequence based timeline.
        """
        return self._get_flame_property("recordOut") - 1

    @property
    def cut_in_frame(self):
        """
        Returns the in frame within the segment.
        This denotes at which frame playback of the segment should start within the
        local media associated with the segment.

        Note that since flame normalizes all sequences as part of its export,
        this value does not correspond to the value found in the original
        sequence data in flame.
        """
        return self._get_flame_property("sourceIn") + self._get_flame_property("handleIn")

    @property
    def cut_out_frame(self):
        """
        Returns the out frame within the segment.
        This denotes at which frame playback of the segment should stop within the
        local media associated with the segment.

        Note that since flame normalizes all sequences as part of its export,
        this value does not correspond to the value found in the original
        sequence data in flame.
        """
        return self._get_flame_property("sourceOut") - self._get_flame_property("handleOut") - 1

    @property
    def head_in_frame(self):
        """
        Returns the in frame within the segment, including any handles.
        """
        return self._get_flame_property("sourceIn")

    @property
    def tail_out_frame(self):
        """
        Returns the out frame within the segment, including any handles
        """
        return self._get_flame_property("sourceOut") - 1

    @property
    def edit_in_timecode(self):
        """
        Returns the in timecode for the edit point
        This denotes where this segment sits in the sequence based timeline.
        """
        return self._frames_to_timecode(
            self.edit_in_frame,
            self.sequence_fps,
            self.sequence_use_drop_frames
        )

    @property
    def edit_out_timecode(self):
        """
        Returns the out timecode for the edit point.
        This denotes where this segment sits in the sequence based timeline.
        """
        return self._frames_to_timecode(
            self.edit_out_frame,
            self.sequence_fps,
            self.sequence_use_drop_frames
        )

    @property
    def cut_in_timecode(self):
        """
        Returns the in timecode within the segment.
        This denotes at which frame playback of the segment should start within the
        local media associated with the segment.

        Note that since flame normalizes all sequences as part of its export,
        this value does not correspond to the value found in the original
        sequence data in flame.
        """
        return self._frames_to_timecode(
            self.cut_in_frame,
            self.fps,
            self.use_drop_frames
        )

    @property
    def cut_out_timecode(self):
        """
        Returns the out timecode within the segment.
        This denotes at which frame playback of the segment should stop within the
        local media associated with the segment.

        Note that since flame normalizes all sequences as part of its export,
        this value does not correspond to the value found in the original
        sequence data in flame.
        """
        return self._frames_to_timecode(
            self.cut_out_frame,
            self.fps,
            self.use_drop_frames
        )

    @property
    def flame_data(self):
        """
        Flame hook data dictionary for this segment.

        See tk-flame/flame_hooks/sg_export_hook.py and
        tk-flame/flame_hooks/sg_batch_hook.py for details on what this
        dictionary can contain.
        """
        return self._flame_data

    def set_flame_data(self, value):
        """
        Set Flame hook data dictionary for this segment.

        See tk-flame/flame_hooks/sg_export_hook.py and
        tk-flame/flame_hooks/sg_batch_hook.py for details on what this
        dictionary can contain.

        :param value: Flame hook data dictionary for this segment.
        """
        self._flame_data = value

    def set_shotgun_version_id(self, version_id):
        """
        Specifies the shotgun version id assocaited with this segment
        :param version_id: version id as int
        """
        self._shotgun_version_id = version_id

    def _get_flame_property(self, property_name):
        """
        Helper method. Safely returns the given property and raises if it doesn't exist.
        :param property_name: Property value to return
        :return: Flame property
        :raises: ValueError if not found
        """
        if self.flame_data is None:
            raise ValueError("No Flame metadata found for %s" % self)

        if property_name not in self.flame_data:
            raise ValueError(
                "Property '%s' not found in Flame metadata for %s" % (property_name, self)
            )

        return self.flame_data[property_name]

    def _frames_to_timecode(self, total_frames, frame_rate, drop):
        """
        Helper method that converts frames to SMPTE timecode.

        :param total_frames: Number of frames
        :param frame_rate: frames per second
        :param drop: true if time code should drop frames, false if not
        :returns: SMPTE timecode as string, e.g. '01:02:12:32' or '01:02:12;32'
        """
        if drop and frame_rate not in [29.97, 59.94]:
            raise NotImplementedError("Time code calculation logic only supports drop frame "
                                      "calculations for 29.97 and 59.94 fps.")

        # for a good discussion around time codes and sample code, see
        # http://andrewduncan.net/timecodes/

        # round fps to the nearest integer
        # note that for frame rates such as 29.97 or 59.94,
        # we treat them as 30 and 60 when converting to time code
        # then, in some cases we 'compensate' by adding 'drop frames',
        # e.g. jump in the time code at certain points to make sure that
        # the time code calculations are roughly right.
        #
        # for a good explanation, see
        # https://documentation.apple.com/en/finalcutpro/usermanual/index.html#chapter=D%26section=6
        fps_int = int(round(frame_rate))

        if drop:
            # drop-frame-mode
            # add two 'fake' frames every minute but not every 10 minutes
            #
            # example at the one minute mark:
            #
            # frame: 1795 non-drop: 00:00:59:25 drop: 00:00:59;25
            # frame: 1796 non-drop: 00:00:59:26 drop: 00:00:59;26
            # frame: 1797 non-drop: 00:00:59:27 drop: 00:00:59;27
            # frame: 1798 non-drop: 00:00:59:28 drop: 00:00:59;28
            # frame: 1799 non-drop: 00:00:59:29 drop: 00:00:59;29
            # frame: 1800 non-drop: 00:01:00:00 drop: 00:01:00;02
            # frame: 1801 non-drop: 00:01:00:01 drop: 00:01:00;03
            # frame: 1802 non-drop: 00:01:00:02 drop: 00:01:00;04
            # frame: 1803 non-drop: 00:01:00:03 drop: 00:01:00;05
            # frame: 1804 non-drop: 00:01:00:04 drop: 00:01:00;06
            # frame: 1805 non-drop: 00:01:00:05 drop: 00:01:00;07
            #
            # example at the ten minute mark:
            #
            # frame: 17977 non-drop: 00:09:59:07 drop: 00:09:59;25
            # frame: 17978 non-drop: 00:09:59:08 drop: 00:09:59;26
            # frame: 17979 non-drop: 00:09:59:09 drop: 00:09:59;27
            # frame: 17980 non-drop: 00:09:59:10 drop: 00:09:59;28
            # frame: 17981 non-drop: 00:09:59:11 drop: 00:09:59;29
            # frame: 17982 non-drop: 00:09:59:12 drop: 00:10:00;00
            # frame: 17983 non-drop: 00:09:59:13 drop: 00:10:00;01
            # frame: 17984 non-drop: 00:09:59:14 drop: 00:10:00;02
            # frame: 17985 non-drop: 00:09:59:15 drop: 00:10:00;03
            # frame: 17986 non-drop: 00:09:59:16 drop: 00:10:00;04
            # frame: 17987 non-drop: 00:09:59:17 drop: 00:10:00;05

            # calculate number of drop frames for a 29.97 std NTSC
            # workflow. Here there are 30*60 = 1800 frames in one
            # minute

            FRAMES_IN_ONE_MINUTE = 1800 - 2

            FRAMES_IN_TEN_MINUTES = (FRAMES_IN_ONE_MINUTE * 10) - 2

            ten_minute_chunks = total_frames / FRAMES_IN_TEN_MINUTES
            one_minute_chunks = total_frames % FRAMES_IN_TEN_MINUTES

            ten_minute_part = 18 * ten_minute_chunks
            one_minute_part = 2 * ((one_minute_chunks - 2) / FRAMES_IN_ONE_MINUTE)

            if one_minute_part < 0:
                one_minute_part = 0

            # add extra frames
            total_frames += ten_minute_part + one_minute_part

            # for 60 fps drop frame calculations, we add twice the number of frames
            if fps_int == 60:
                total_frames = total_frames * 2

            # time codes are on the form 12:12:12;12
            smpte_token = ";"

        else:
            # time codes are on the form 12:12:12:12
            smpte_token = ":"

        # now split our frames into time code
        hours = int(total_frames / (3600 * fps_int))
        minutes = int(total_frames / (60 * fps_int) % 60)
        seconds = int(total_frames / fps_int % 60)
        frames = int(total_frames % fps_int)
        return "%02d:%02d:%02d%s%02d" % (hours, minutes, seconds, smpte_token, frames)

