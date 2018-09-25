# Copyright (c) 2014 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os


def _show_publisher():
    """
    Show the publisher application
    """

    import sgtk

    engine = sgtk.platform.current_engine()
    if engine is None:
        return

    publisher = engine.apps.get("tk-multi-publish2")
    if publisher and not os.environ.get("SHOTGUN_DISABLE_POST_RENDER_PUBLISH"):
        if engine.export_info:
            tk_multi_publish2 = publisher.import_module("tk_multi_publish2")
            tk_multi_publish2.show_dialog(publisher)


def batchSetupLoaded(setupPath):
    """
    Hook called when a batch setup is loaded.

    :param setupPath: File path of the setup being loaded.
    """
    import sgtk
    engine = sgtk.platform.current_engine()

    # We can't do anything without the Shotgun engine.
    # The engine is None when the user decides to not use the plugin for the project.
    if engine is None:
        return

    engine.trigger_batch_callback("batchSetupLoaded", {"setupPath": setupPath})


def batchSetupSaved(setupPath):
    """
    Hook called when a batch setup is saved.

    :param setupPath: File path of the setup being loaded.
    """
    import sgtk
    engine = sgtk.platform.current_engine()

    # We can't do anything without the Shotgun engine.
    # The engine is None when the user decides to not use the plugin for the project.
    if engine is None:
        return

    engine.trigger_batch_callback("batchSetupSaved", {"setupPath": setupPath})


def batchRenderBegin(info, userData, *args, **kwargs):
    """
    Hook called before a render begins. The render will be blocked
    until this function returns.


    :param info: Empty dictionary for now. Might have parameters in the future.

    :param userData: Object that will be carried over into the render end hooks.
                     This can be used by the hook to pass black box data around.

    :note: This hook is available in Flame 2019.1 and up only.
    """
    import sgtk
    engine = sgtk.platform.current_engine()

    # We can't do anything without the Shotgun engine.
    # The engine is None when the user decides to not use the plugin for the project.
    if engine is None:
        return

    engine.clear_export_info()

    engine.trigger_batch_callback("batchRenderBegin", info)


def batchRenderEnd(info, userData, *args, **kwargs):
    """
    Hook called before a render ends.


    :param info: Dictionary with a number of parameters:

        aborted:              Indicate if the render has been aborted by the user.

    :param userData: Object that could have been populated by the render begin hook.
                     This can be used by the hook to pass black box data around.

    :note: This hook is available in Flame 2019.1 and up only.
    """
    import sgtk
    engine = sgtk.platform.current_engine()

    # We can't do anything without the Shotgun engine.
    # The engine is None when the user decides to not use the plugin for the project.
    if engine is None:
        return

    engine.trigger_batch_callback("batchRenderEnd", info)

    if info.get("aborted", False):
        return

    if isinstance(engine.export_info, list) and len(engine.export_info) > 0:
        _show_publisher()

# tell Flame not to display the fish cursor while we process the hook
batchRenderEnd.func_dict["waitCursor"] = False


def batchExportBegin(info, userData):
    """
    Hook called before an export begins. The export will be blocked
    until this function returns.  Note that for stereo export this
    function will be called twice (for left then right channel)


    :param info: Dictionary with a number of parameters:

        nodeName:             Name of the export node.
        exportPath:           [Modifiable] Export path as entered in the application UI.
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


    :param userData: Object that could have been populated by previous export hooks and that
                     will be carried over into the subsequent export hooks.
                     This can be used by the hook to pass black box data around.
    """
    import sgtk
    engine = sgtk.platform.current_engine()

    # We can't do anything without the Shotgun engine.
    # The engine is None when the user decides to not use the plugin for the project.
    if engine is None:
        return

    engine.trigger_batch_callback("batchExportBegin", info)


def batchExportEnd(info, userData):
    """
    Hook called when an export ends. Note that for stereo export this
    function will be called twice (for left then right channel)

    This function complements the above batchExportBegin function.

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


    :param userData: Object that could have been populated by previous export hooks and that
                     will be carried over into the subsequent export hooks.
                     This can be used by the hook to pass black box data around.
    """
    import sgtk
    engine = sgtk.platform.current_engine()

    # We can't do anything without the Shotgun engine.
    # The engine is None when the user decides to not use the plugin for the project.
    if engine is None:
        return

    engine.trigger_batch_callback("batchExportEnd", info)

    if not info.get("aborted", False):
        engine.cache_batch_export_asset(info)


# tell Flame not to display the fish cursor while we process the hook
batchExportEnd.func_dict["waitCursor"] = False
