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

# We have the situation where we need the base_hooks module to be accessible
# when building docs, but since the tk_hiero_export module requires the
# hiero API, it can't be imported from outside of Nuke Studio/Hiero. What
# we do is keep the base_hooks module outside of tk_hiero_export, which is
# where it's imported from when building docs, and then we import the
# hook base classes here to make them easily accessible from within this
# module.
try:
    # We want the app's top-level python directory, so we go one level
    # up from current.
    sys.path.append(
        os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                ".."
            )
        )
    )
    from base_hooks import (
        HieroCustomizeExportUI,
        HieroUpdateCuts,
        HieroUpdateShot,
        HieroGetExtraPublishData,
        HieroGetQuicktimeSettings,
        HieroPostVersionCreation,
        HieroPreExport,
        HieroResolveCustomStrings,
        HieroTranslateTemplate,
        HieroUpdateVersionData,
        HieroUploadThumbnail,
        HieroGetShot,
    )
finally:
    sys.path.pop()

from .base import ShotgunHieroObjectBase

from .sg_shot_processor import (
	ShotgunShotProcessor,
	ShotgunShotProcessorUI,
	ShotgunShotProcessorPreset,
)

from .shot_updater import ShotgunShotUpdater, ShotgunShotUpdaterPreset
from .version_creator import ShotgunTranscodeExporterUI, ShotgunTranscodeExporter, ShotgunTranscodePreset
from .sg_nuke_shot_export import ShotgunNukeShotExporterUI, ShotgunNukeShotExporter, ShotgunNukeShotPreset
from .sg_audio_export import ShotgunAudioExporterUI, ShotgunAudioExporter, ShotgunAudioPreset
