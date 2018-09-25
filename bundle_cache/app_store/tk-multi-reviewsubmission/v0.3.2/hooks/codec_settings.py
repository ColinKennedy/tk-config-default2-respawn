# Copyright (c) 2015 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that controls various codec settings when submitting items for review
"""
import sgtk
import os
import sys

import nuke

HookBaseClass = sgtk.get_hook_baseclass()

class CodecSettings(HookBaseClass):

    def get_quicktime_settings(self, **kwargs):
        """
        Allows modifying default codec settings for Quicktime generation.
        Returns a dictionary of settings to be used for the Write Node that generates
        the Quicktime in Nuke.
        """
        settings = {}
        if sys.platform in ["darwin", "win32"]:
            settings["file_type"] = "mov"
            if nuke.NUKE_VERSION_MAJOR >= 9:
                # Nuke 9.0v1 changed the codec knob name to meta_codec and added an encoder knob
                # (which defaults to the new mov64 encoder/decoder).                  
                settings["meta_codec"] = "jpeg"
                settings["mov64_quality_max"] = "3"
            else:
                settings["codec"] = "jpeg"

        elif sys.platform == "linux2":
            if nuke.NUKE_VERSION_MAJOR >= 9:
                # Nuke 9.0v1 removed ffmpeg and replaced it with the mov64 writer
                # http://help.thefoundry.co.uk/nuke/9.0/#appendices/appendixc/supported_file_formats.html
                settings["file_type"] = "mov64"
                settings["mov64_codec"] = "jpeg"
                settings["mov64_quality_max"] = "3"
            else:
                # the 'codec' knob name was changed to 'format' in Nuke 7.0
                settings["file_type"] = "ffmpeg"
                settings["format"] = "MOV format (mov)"

        return settings
