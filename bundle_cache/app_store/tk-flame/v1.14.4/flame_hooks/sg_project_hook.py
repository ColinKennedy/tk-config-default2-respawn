# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

# Note! This file implements the projectHook interface from Flame 2015.2
        
def appInitialized(projectName):
    """
    Hook called when application is fully initialized.
    
    :param projectName: String containing the name of the project that was loaded
    """
    
    # attempt to start the Flame engine if it hasn't already been started.
    
    import sgtk
    import os    

    engine = sgtk.platform.current_engine()

    if engine:
        # there is already an engine running.
        # TODO: later on, allow for switching of engines as projects 
        # are being switched. For now, issue a warning
        #
        # NOTE/UPDATE: Cross-project changes actually partially work
        # now. It appears as though the Toolkit portion of the process
        # works fine, in that the old engine is torn down and sgtk is
        # re-bootstrapped into the new project/environment without any
        # problems. However, it looks as though the classic sg shots
        # export right-click-menu action doesn't show up when switching
        # from a zero config project to a classic config project.
        #
        # NOTE: We also don't know that the Flame hooks are properly
        # repopulated when switching across project boundaries. That is
        # something that will need to be investigated before we can be
        # certain that it's entirely safe.
        #
        # We only care to alert the user if the change in Flame project
        # is going to send us to a different Shotgun project. If we're
        # not crossing project boundaries, there are no concerns about
        # hooks, paths (for classic projects), and the like.
        project_is_changing = True

        try:
            import flame
        except Exception:
            engine.logger.debug(
                "Was unable to import the flame Python module. As such, "
                "it must be assumed that the Flame project change is "
                "resulting in a change in Shotgun project. This means "
                "that the user will see a QMessageBox warning if the "
                "tk-flame engine's project_switching setting is false. "
                "The API to allow this was introduced in 2018.2."
            )
        else:
            try:
                current_flame_project = flame.project.current_project
                new_sg_project = current_flame_project.shotgun_project_name.get_value()
            except Exception:
                engine.logger.debug(
                    "Failed to get the SG project from the current Flame project. "
                    "As a result, falling back on the engine's project_switching "
                    "setting to determine whether to show the user a warning stating "
                    "that project switching might not behave as expected."
                )
            else:
                project_is_changing = (new_sg_project != engine.context.project.get("name"))

        if engine.get_setting("project_switching") is False and project_is_changing:
            from sgtk.platform.qt import QtGui
            QtGui.QMessageBox.warning(
                None,
                "No project switching!",
                "The Shotgun integration does not currently support project switching.\n"
                "Even if you switch projects, any Shotgun-specific configuration will\n"
                "remain connected to the initially loaded project."
            )
    
    else:
        # no engine running - so start one!
        engine_name = os.environ.get("TOOLKIT_ENGINE_NAME")
        toolkit_context = os.environ.get("TOOLKIT_CONTEXT")
        
        if toolkit_context is None:
            logger = sgtk.LogManager.get_logger(__name__)
            logger.debug("No toolkit context, can't initialize the engine")
            return
        
        context = sgtk.context.deserialize(toolkit_context)
        
        # set a special environment variable to help hint to the engine
        # that we are running a backburner job
        os.environ["TOOLKIT_FLAME_ENGINE_MODE"] = "DCC"
        e = sgtk.platform.start_engine(engine_name, context.sgtk, context)
        del os.environ["TOOLKIT_FLAME_ENGINE_MODE"]
        
        # pass the python executable from the bootstrap to the engine 
        python_executable = os.environ.get("TOOLKIT_FLAME_PYTHON_BINARY")
        if not python_executable:
            e.log_error("Cannot find environment variable TOOLKIT_FLAME_PYTHON_BINARY")
        else:
            e.set_python_executable(python_executable)

        install_root = os.environ.get("TOOLKIT_FLAME_INSTALL_ROOT")
        if not install_root:
            e.log_error("Cannot find environment variable TOOLKIT_FLAME_INSTALL_ROOT")
        else:
            e.set_install_root(install_root)

        # and the version number
        major_version_str = os.environ.get("TOOLKIT_FLAME_MAJOR_VERSION")
        minor_version_str = os.environ.get("TOOLKIT_FLAME_MINOR_VERSION")
        patch_version_str = os.environ.get("TOOLKIT_FLAME_PATCH_VERSION")
        full_version_str = os.environ.get("TOOLKIT_FLAME_VERSION")
        
        if None in (major_version_str, minor_version_str, patch_version_str, full_version_str):
            e.log_error("Cannot find environment variable TOOLKIT_FLAME_x_VERSION")
        else:
            e.set_version_info(
                major_version_str=major_version_str,
                minor_version_str=minor_version_str,
                patch_version_str=patch_version_str,
                full_version_str=full_version_str
            )
        
        
