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
import os


HookBaseClass = sgtk.get_hook_baseclass()

class ExportSettings(HookBaseClass):
    """
    This hook controls the settings that Flame will use when it exports the quicktimes 
    prior to uploading them to Shotgun. It also lets a user control where on disk temporary
    quicktime files will be located.
    """

    def get_export_preset(self):
        """
        Return the path to a Flame export preset that should be used when generating 
        a sequence quicktime.
        
        :returns: Path on disk to Flame export preset 
        """
        # Use the "Submit for review" preset if it exist. This preset is packaged with flame 
        # in new version and will point to an available codec depending on the flavour. This
        # also give the opportunity to clients to override this preset if needs be.
        preset_path = os.path.join(
            self.parent.engine.export_presets_root,
            "movie_file",
            "Submit for review.xml"
        )
        if os.access(preset_path, os.R_OK) :
            return preset_path
 
        # fallback on one of the default presets that ship with Flame.
        return os.path.join(
            self.parent.engine.export_presets_root,
            "movie_file",
            "QuickTime (H.264 720p 8Mbits).xml"
        )
