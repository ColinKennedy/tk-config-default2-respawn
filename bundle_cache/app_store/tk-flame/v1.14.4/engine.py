# Copyright (c) 2014 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
A Toolkit engine for Flame
"""

import os
import pwd
import re
import shlex
import sys
import uuid
import sgtk
import pickle
import logging
import pprint
import logging.handlers
import traceback
import datetime
import subprocess
from sgtk import TankError

LOG_CHANNEL = "sgtk.tk-flame"


class FlameEngine(sgtk.platform.Engine):
    """
    The engine class. This wraps around a series of callbacks in Flame (so called hooks).
    The Flame engine is a bit different than other engines.

    Because Flame doesn't have an API, we cannot call Flame, but Flame will call out
    to the toolkit code. This means that the normal register_command approach won't
    work inside of Flame - instead, the engine introduces a different scheme of callbacks
    that apps can register to ensure that they cen do stuff.

    For apps, the main entry points are register_export_hook and register_batch_hook.
    For more information, see below.
    """

    # the name of the folder in the engine which we should register
    # with Flame to trigger various hooks to run.
    FLAME_HOOKS_FOLDER = "flame_hooks"

    # our default log file to write to
    SGTK_LOG_FILE = "tk-flame.log"

    # a 'plan B' safe log file that we call fall back on in case
    # the default log file cannot be accessed
    SGTK_LOG_FILE_SAFE = "/tmp/tk-flame.log"

    # define constants for the various modes the engine can execute in
    (ENGINE_MODE_DCC, ENGINE_MODE_PRELAUNCH, ENGINE_MODE_BACKBURNER) = range(3)

    @property
    def host_info(self):
        """
        :returns: A dictionary with information about the application hosting this engine.

        The returned dictionary is of the following form on success:

            {
                "name": "Flame",
                "version": "2018.3.pr84",
            }

        The returned dictionary is of following form on an error preventing
        the version identification.

            {
                "name": "Flame",
                "version": "unknown"
            }
        """
        host_info = {"name": "Flame", "version": "unknown"}

        try:
            # The 'SHOTGUN_FLAME_VERSION' environment variable comes from Flame plugin
            # The 'TOOLKIT_FLAME_VERSION' environment variable comes from Flame classic config
            if "SHOTGUN_FLAME_VERSION" in os.environ:
                host_info["version"] = os.environ.get("SHOTGUN_FLAME_VERSION", "unknown")

            elif "TOOLKIT_FLAME_VERSION" in os.environ:
                host_info["version"] = os.environ.get("TOOLKIT_FLAME_VERSION", "unknown")

        except:
            # Fallback to initialization value above
            pass

        return host_info

    def __init__(self, *args, **kwargs):
        """
        Overridden constructor where we init some things which
        need to be defined very early on in the engine startup.
        """

        # to support use cases where the flame engine isn't started via
        # the multi-launchapp chain, make sure that hooks that the engine
        # implements are registered.
        flame_hooks_folder = os.path.join(self.disk_location, self.FLAME_HOOKS_FOLDER)
        sgtk.util.append_path_to_env_var("DL_PYTHON_HOOK_PATH", flame_hooks_folder)
        self.log_debug("Added to hook path: %s" % flame_hooks_folder)

        # the path to the associated python executable
        self._python_executable_path = None

        # version of Flame we are running
        self._flame_version = None

        # root folder where flame is installed
        self._install_root = None

        # set the current engine mode. The mode contains information about
        # how the engine was started - it can be executed either before the
        # actual DCC starts up (pre-launch), in the DCC itself or on the
        # backburner farm. This means that there are three distinct bootstrap
        # scripts which can launch the engine (all contained within the engine itself).
        # these bootstrap scripts all set an environment variable called
        # TOOLKIT_FLAME_ENGINE_MODE which defines the desired engine mode.
        engine_mode_str = os.environ.get("TOOLKIT_FLAME_ENGINE_MODE")
        if engine_mode_str == "PRE_LAUNCH":
            self._engine_mode = self.ENGINE_MODE_PRELAUNCH
        elif engine_mode_str == "BACKBURNER":
            self._engine_mode = self.ENGINE_MODE_BACKBURNER
        elif engine_mode_str == "DCC":
            self._engine_mode = self.ENGINE_MODE_DCC
        else:
            raise TankError("Unknown launch mode '%s' defined in "
                            "environment variable TOOLKIT_FLAME_ENGINE_MODE!" % engine_mode_str)

        # Transcoder, thumbnail generator and local movie generator will be
        # initialized on first request for them since, in order to know which
        # type we will need, we need to wait for the Flame API to be loaded
        # completely.
        #
        self._transcoder = None
        self._thumbnail_generator = None
        self._local_movie_generator = None

        super(FlameEngine, self).__init__(*args, **kwargs)

    def pre_app_init(self):
        """
        Engine construction/setup done before any apps are initialized
        """
        # set up a custom exception trap for the engine.
        # it will log the exception and if possible also
        # display it in a UI
        sys.excepthook = sgtk_exception_trap

        # now start the proper init
        self.log_debug("%s: Initializing..." % self)

        # maintain a list of export options
        self._registered_export_instances = {}
        self._export_sessions = {}
        self._registered_batch_instances = []

        # maintain the export cache
        self._export_info = None

        if self.has_ui:
            # tell QT to interpret C strings as utf-8
            from sgtk.platform.qt import QtCore, QtGui
            utf8 = QtCore.QTextCodec.codecForName("utf-8")
            QtCore.QTextCodec.setCodecForCStrings(utf8)

        # Assuming we're in a new enough version of Flame (2018.3+) we'll
        # be able to link the Flame project to our SG project. This will
        # ensure that is a use launches Flame's plugin-based Shotgun
        # integration that they will be bootstrapped into the correct
        # project and won't be prompted to choose an SG project to link to.
        #
        # NOTE: We only take the initiative here and create the project
        # link if this is a classic config launch of Flame. One quick way
        # to knwo that is to just refer to the environment, where we know
        # that the classic startup script sets some variables.
        if "TOOLKIT_ENGINE_NAME" in os.environ:
            try:
                import flame
            except Exception:
                self.logger.debug(
                    "Was unable to import the flame Python module. As a result, "
                    "the Flame project will not be linked to associated Shotgun "
                    "project using the Flame Python API. This shouldn't cause "
                    "any problems in the current session, but it does mean "
                    "that the user might be prompted to link this project to a "
                    "Shotgun project if they launch Flame using the Toolkit "
                    "plugin and open this same Flame project."
                )
            else:
                try:
                    current_flame_project = flame.project.current_project
                    current_flame_project.shotgun_project_name = self.context.project.get("name")
                except Exception:
                    self.logger.debug(
                        "Was unable to set the current Flame project's "
                        "shotgun_project_name property. This shouldn't cause "
                        "any problems in the current session, but it does mean "
                        "that the user might be prompted to link this project to a "
                        "Shotgun project if they launch Flame using the Toolkit "
                        "plugin and open this same Flame project."
                    )
                else:
                    self.logger.debug(
                        "Successfully linked the Flame project to its associated "
                        "Shotgun project."
                    )

    def _initialize_logging(self, install_root):
        """
        Set up logging for the engine

        :param install_root: path to flame install root
        """
        # standard flame log file
        std_log_file = os.path.join(install_root, "log", self.SGTK_LOG_FILE)

        # test if we can write to the default log file
        if os.access(os.path.dirname(std_log_file), os.W_OK):
            log_file = std_log_file
            using_safe_log_file = False
        else:
            # cannot rotate file in this directory, write to tmp instead.
            log_file = self.SGTK_LOG_FILE_SAFE
            using_safe_log_file = True

        # Set up a rotating logger with 4MiB max file size
        if using_safe_log_file:
            rotating = logging.handlers.RotatingFileHandler(log_file, maxBytes=4 * 1024 * 1024, backupCount=10)
        else:
            rotating = logging.handlers.RotatingFileHandler(log_file, maxBytes=0, backupCount=50, delay=True)
            # Always rotate. Current user might not have the correct permission to open this file
            if os.path.exists(log_file):
                rotating.doRollover()  # Will open file after roll over

        rotating.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] PID %(process)d: %(message)s"))
        # create a global logging object
        logger = logging.getLogger(LOG_CHANNEL)
        logger.propagate = False
        # clear any existing handlers
        logger.handlers = []
        logger.addHandler(rotating)
        if self.get_setting("debug_logging"):
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        # now that we have a logger, we can warn about a non-std log file :)
        if using_safe_log_file:
            logger.error("Cannot write to standard log file location %s! Please check "
                         "the filesystem permissions. As a fallback, logs will be "
                         "written to %s instead." % (std_log_file, log_file))

    def set_python_executable(self, python_path):
        """
        Specifies the path to the associated python process.
        This is typically populated as part of the engine startup.

        :param python_path: path to python, as string
        """
        self._python_executable_path = python_path
        self.log_debug("This engine is running python interpreter '%s'" % self._python_executable_path)

    def set_version_info(self, major_version_str, minor_version_str, full_version_str, patch_version_str="0"):
        """
        Specifies which version of Flame this engine is running.
        This is typically populated as part of the engine startup.

        :param major_version_str: Major version number as string
        :param minor_version_str: Minor version number as string
        :param patch_version_str: Patch version number as string
        :param full_version_str: Full version number as string
        """
        self._flame_version = {"full": full_version_str, "major": major_version_str, "minor": minor_version_str,
                               "patch": patch_version_str}
        self.log_debug("This engine is running with Flame version '%s'" % self._flame_version)

    def set_install_root(self, install_root):
        """
        Specifies where the flame installation is located.

        this may be '/usr/discreet', '/opt/Autodesk' etc.

        :param install_root: root path to flame installation
        """
        if self._install_root:
            # cannot call this multiple times
            raise TankError("Cannot call set_install_root multiple times!")

        self.log_debug("Flame install root is '%s'" % self._install_root)
        self._install_root = install_root
        self._initialize_logging(install_root)

    def _get_commands_matching_setting(self, setting):
        """
        This expects a list of dictionaries in the form:
            {name: "command-name", app_instance: "instance-name", display_name: "Display Name"  }

        The app_instance value will match a particular app instance associated with
        the engine. The name is the menu name of the command to run when the engine starts up. The
        display_name is the menu display name of the command to run.

        If name is '' then all commands from the given app instance are returned.
        If display_name is not present, name will be used instead.

        :returns A list of tuples for all commands that match the given setting.
                 Each tuple will be in the form (instance_name, display_name, command_name, callback)
        """
        # return a dictionary grouping all the commands by instance name
        commands_by_instance = {}
        for (name, value) in self.commands.iteritems():
            app_instance = value["properties"].get("app")
            if app_instance:
                instance_name = app_instance.instance_name
            else:
                # A command without an app instance in the context menu is actually coming from the engine, so we'll
                # use the engine name instead.
                instance_name = "tk-flame"

            commands_by_instance.setdefault(instance_name, []).append((name, value["callback"]))

        # go through the values from the setting and return any matching commands
        ret_value = []
        setting_value = self.get_setting(setting, [])
        for command in setting_value:
            command_name = command["name"]
            instance_name = command["app_instance"]
            display_name = command.get("display_name", command_name)
            instance_commands = commands_by_instance.get(instance_name)

            if instance_commands is None:
                continue

            for (name, callback) in instance_commands:
                # add the command if the name from the settings is '' or the name matches
                if not command_name or (command_name == name):
                    ret_value.append((instance_name, display_name, name, callback))

        return ret_value

    def post_app_init(self):
        """
        Do any initialization after apps have been loaded
        """
        self.log_debug("%s: Running post app init..." % self)

        # only run the startup commands when in DCC mode
        if self._engine_mode != self.ENGINE_MODE_DCC:
            return

        # run any commands registered via run_at_startup
        commands_to_start = self._get_commands_matching_setting("run_at_startup")
        for (instance_name, command_name, callback) in commands_to_start:
            self.log_debug("Running at startup: (%s, %s)" % (instance_name, command_name))
            callback()

    def destroy_engine(self):
        """
        Called when the engine is being destroyed
        """
        self.log_debug("%s: Destroying..." % self)

        # Remove the current engine python hooks from the flame python hooks path
        env_var_sep = ":"
        env_var_name = "DL_PYTHON_HOOK_PATH"
        flame_hooks_folder = os.path.join(self.disk_location, self.FLAME_HOOKS_FOLDER)
        paths = os.environ.get(env_var_name, "").split(env_var_sep)
        paths = [path for path in paths if path != flame_hooks_folder]
        os.environ[env_var_name] = env_var_sep.join(paths)
        self.log_debug("Removed to hook paths: %s" % flame_hooks_folder)

        # Close every app windows
        self.close_windows()

    @property
    def flame_main_window(self):
        """
        Returns the Flame's main window
        :return: Widget representing the flame's main window.
        """
        from sgtk.platform.qt import QtCore, QtGui

        for w in QtGui.QApplication.topLevelWidgets():
            if w.objectName() == "CF Main Window":
                self.log_debug("Found Flame main window (%s)" % w.windowTitle())
                return w

    @property
    def python_executable(self):
        """
        Returns the python executable associated with this engine

        :returns: path to python, e.g. '/usr/discreet/python/2016.0.0.322/bin/python'
        """
        if self._python_executable_path is None:
            raise TankError("Python executable has not been defined for this engine instance!")

        return self._python_executable_path

    @property
    def preset_version(self):
        """
        Returns the preset version required for the currently executing
        version of Flame. Preset xml files in Flame all have a version number
        to denote which generation of the file format they implement. If you are using
        an old preset with a new version of Flame, a warning message appears.

        :returns: Preset version, as string, e.g. '5'
        """
        if self._flame_version is None:
            raise TankError("Cannot determine preset version - No Flame DCC version specified!")

        if self.is_version_less_than("2016.1"):
            # for version 2016 before ext 1, export preset is v5
            return "5"
        elif self.is_version_less_than("2017"):
            # flame 2016 extension 1 and above.
            return "6"
        else:
            # flame 2017 and above
            #
            # Note: Flame 2017 uses preset 7, however further adjustments to the actual
            #       preset format used is required in individual apps - for the time being,
            #       the preset version is held at v6, ensuring that app apps operate correctly,
            #       but generating a warning message at startup.
            #
            return "7"

    @property
    def export_presets_root(self):
        """
        The location where flame export presets are located

        :returns: Path as string
        """

        # If possible use the Flame python API to get the presets location
        try:
            import flame
            if 'PyExporter' in dir(flame):
                return flame.PyExporter.get_presets_base_dir(
                    flame.PyExporter.PresetVisibility.Shotgun)
        except:
            pass

        if self.is_version_less_than("2017"):
            # flame 2016 presets structure
            return os.path.join(
                self.install_root,
                "presets",
                self.flame_version,
                "export",
                "presets"
            )
        else:
            # flame 2017+ presets structure (note the extra flame folder)
            return os.path.join(
                self.install_root,
                "presets",
                self.flame_version,
                "export",
                "presets",
                "flame"
            )

    @staticmethod
    def _get_full_preset_path(preset_path, preset_type):
        """
        Convert a path to a preset that can be incomplete to an absolute path.

        :param preset_path: Path to a preset to find.
        :param preset_type: Type of preset to look for.

        :returns: Absolute path to the preset.
        """
        if not os.path.isabs(preset_path):
            import flame
            presets_dir = flame.PyExporter.get_presets_dir(
                flame.PyExporter.PresetVisibility.Shotgun,
                preset_type
            )
            preset_path = os.path.join(
                presets_dir,
                preset_path
            )
        return preset_path

    @property
    def thumbnails_preset_path(self):
        """
        The location of the flame export preset to use to generate thumbnails.

        :returns: Path as string
        """
        import flame
        return self._get_full_preset_path(
            self.get_setting("thumbnails_preset_path"),
            flame.PyExporter.PresetType.Image_Sequence
        )

    @property
    def previews_preset_path(self):
        """
        The location of the flame export preset to use to generate previews.

        :returns: Path as string
        """
        import flame
        return self._get_full_preset_path(
            self.get_setting("previews_preset_path"),
            flame.PyExporter.PresetType.Movie
        )

    @property
    def local_movies_preset_path(self):
        """
        The location of the flame export preset to use to generate local movies.

        Local movies are linked to assets in Shotgun thru the "Path to Movie"
        field but are not uploaded on the server.

        :returns: Path as string
        """
        import flame
        return self._get_full_preset_path(
            self.get_setting("local_movies_preset_path"),
            flame.PyExporter.PresetType.Movie
        )

    @property
    def wiretap_tools_root(self):
        """
        The location of wiretap tool

        :returns: Path as string
        """
        return os.path.join(
            self.install_root,
            "wiretap",
            "tools",
            self.flame_version
        )

    def _is_version_less_than(self, major, minor, patch):
        """
        Compares the given version numbers with the current
        flame version and returns False if the given version is
        greater than the current version.

        Example:

        - Flame: '2016.1.0.278', version str: '2016.1' => False
        - Flame: '2016',  version str: '2016.1' => True

        :param version_str: Version to run comparison against
        """
        if int(self.flame_major_version) != int(major):
            return int(self.flame_major_version) < int(major)

        if int(self.flame_minor_version) != int(minor):
            return int(self.flame_minor_version) < int(minor)

        if int(self.flame_patch_version) != int(patch):
            return int(self.flame_patch_version) < int(patch)

        # Same version
        return False

    def is_version_less_than(self, version_str):
        """
        Compares the given version string with the current
        flame version and returns False if the given version is
        greater than the current version.

        Example:

        - Flame: '2016.1.0.278', version str: '2016.1' => False
        - Flame: '2016',  version str: '2016.1' => True

        :param version_str: Version to run comparison against
        """

        major_ver = 0
        minor_ver = 0
        patch_ver = 0

        chunks = version_str.split(".")
        if len(chunks) > 0:
            if chunks[0].isdigit():
                major_ver = int(chunks[0])

        if len(chunks) > 1:
            if chunks[1].isdigit():
                minor_ver = int(chunks[1])

        if len(chunks) > 2:
            if chunks[2].isdigit():
                patch_ver = int(chunks[2])

        return self._is_version_less_than(major_ver, minor_ver, patch_ver)

    @property
    def flame_major_version(self):
        """
        Returns Flame's major version number as a string.

        :returns: String (e.g. '2016')
        """
        if self._flame_version is None:
            raise TankError("No Flame DCC version specified!")

        return self._flame_version["major"]

    @property
    def flame_minor_version(self):
        """
        Returns Flame's minor version number as a string.

        :returns: String (e.g. '2')
        """
        if self._flame_version is None:
            raise TankError("No Flame DCC version specified!")

        return self._flame_version["minor"]

    @property
    def flame_patch_version(self):
        """
        Returns Flame's patch version number as a string.

        :returns: String (e.g. '2')
        """
        if self._flame_version is None:
            raise TankError("No Flame DCC version specified!")

        return self._flame_version["patch"]

    @property
    def flame_version(self):
        """
        Returns Flame's full version number as a string.

        :returns: String (e.g. '2016.1.0.278')
        """
        if self._flame_version is None:
            raise TankError("No Flame DCC version specified!")

        return self._flame_version["full"]

    @property
    def install_root(self):
        """
        The location where flame is installed.

        This may be '/usr/discreet', '/opt/Autodesk' etc.

        :returns: Path as string
        """
        return self._install_root

    @property
    def has_ui(self):
        """
        Property to determine if the current environment has access to a UI or not
        """
        # check if there is a UI. With Flame, we may run the engine in bootstrap
        # mode or on the farm - in this case, there is no access to UI. If inside the
        # DCC UI environment, pyside support is available.
        has_ui = False
        try:
            from sgtk.platform.qt import QtCore, QtGui
            if QtCore.QCoreApplication.instance():
                # there is an active application
                has_ui = True
        except:
            pass

        return has_ui

    def show_panel(self, panel_id, title, bundle, widget_class, *args, **kwargs):
        """
        Override the base show_panel to create a non-modal dialog that will stay on
        top of the Flame interface
        """
        if not self.has_ui:
            self.log_error("Sorry, this environment does not support UI display! Cannot show "
                           "the requested panel '%s'." % title)
            return None

        from sgtk.platform.qt import QtCore, QtGui

        # create the dialog:
        dialog, widget = self._create_dialog_with_widget(title, bundle, widget_class, *args, **kwargs)
        dialog.setWindowFlags(
            dialog.windowFlags() |
            QtCore.Qt.WindowStaysOnTopHint &
            ~QtCore.Qt.WindowCloseButtonHint
        )

        self.created_qt_dialogs.append(dialog)

        # show the dialog
        dialog.show()

        # lastly, return the instantiated widget
        return widget

    def _get_dialog_parent(self):
        """
        Get the QWidget parent for all dialogs created through :meth:`show_dialog` :meth:`show_modal`.

        Can be overriden in derived classes to return the QWidget to be used as the parent
        for all TankQDialog's.

        :return: QT Parent window (:class:`PySide.QtGui.QWidget`)
        """
        from sgtk.platform.qt import QtCore, QtGui

        w = self.flame_main_window

        return w if w else super(FlameEngine, self)._get_dialog_parent()

    def show_dialog(self, title, bundle, widget_class, *args, **kwargs):
        """
        Shows a non-modal dialog window in a way suitable for this engine.
        The engine will attempt to parent the dialog nicely to the host application.
        The dialog will be created with a standard Toolkit window title bar where
        the title will be displayed.

        .. note:: In some cases, it is necessary to hide the standard Toolkit title
                  bar. You can do this by adding a property to the widget class you are
                  displaying::

                        @property
                        def hide_tk_title_bar(self):
                            "Tell the system to not show the standard toolkit toolbar"
                            return True

        **Notes for engine developers**

        Qt dialog & widget management can be quite tricky in different engines/applications.
        Because of this, Sgtk provides a few overridable methods with the idea being that when
        developing a new engine, you only need to override the minimum amount necessary.

        Making use of these methods in the correct way allows the base Engine class to manage the
        lifetime of the dialogs and widgets efficiently and safely without you having to worry about it.

        The methods available are listed here in the hierarchy in which they are called::

            show_dialog()/show_modal()
                _create_dialog_with_widget()
                    _get_dialog_parent()
                    _create_widget()
                    _create_dialog()

        For example, if you just need to make sure that all dialogs use a specific parent widget
        then you only need to override _get_dialog_parent() (e.g. the tk-maya engine).
        However, if you need to implement a two-stage creation then you may need to re-implement
        show_dialog() and show_modal() to call _create_widget() and _create_dialog() directly rather
        than using the helper method _create_dialog_with_widget() (e.g. the tk-3dsmax engine).
        Finally, if the application you are writing an engine for is Qt based then you may not need
        to override any of these methods (e.g. the tk-nuke engine).

        :param title: The title of the window. This will appear in the Toolkit title bar.
        :param bundle: The app, engine or framework object that is associated with this window
        :param widget_class: The class of the UI to be constructed. This must derive from QWidget.
        :type widget_class: :class:`PySide.QtGui.QWidget`

        Additional parameters specified will be passed through to the widget_class constructor.

        :returns: the created widget_class instance
        """
        if not self.has_ui:
            self.log_error("Sorry, this environment does not support UI display! Cannot show "
                           "the requested window '%s'." % title)
            return None

        from sgtk.platform.qt import QtGui, QtCore

        # create the dialog:
        dialog, widget = self._create_dialog_with_widget(title, bundle, widget_class, *args, **kwargs)

        dialog.setWindowFlags(
            dialog.windowFlags() |
            QtCore.Qt.WindowStaysOnTopHint &
            ~QtCore.Qt.WindowCloseButtonHint
        )

        self.created_qt_dialogs.append(dialog)

        # show the dialog
        dialog.show()

        # lastly, return the instantiated widget
        return widget

    def close_windows(self):
        """
        Closes the various windows (dialogs, panels, etc.) opened by the engine.
        """

        # Make a copy of the list of Tank dialogs that have been created by the engine and
        # are still opened since the original list will be updated when each dialog is closed.
        opened_dialog_list = self.created_qt_dialogs[:]

        # Loop through the list of opened Tank dialogs.
        for dialog in opened_dialog_list:
            dialog_window_title = dialog.windowTitle()
            try:
                # Close the dialog and let its close callback remove it from the original dialog list.
                self.log_debug("Closing dialog %s." % dialog_window_title)
                dialog.close()
            except Exception, exception:
                self.log_error("Cannot close dialog %s: %s" % (dialog_window_title, exception))

    def log_debug(self, msg):
        """
        Log a debug message

        :param msg: The debug message to log
        """
        logging.getLogger(LOG_CHANNEL).debug(msg)

    def log_info(self, msg):
        """
        Log some info

        :param msg: The info message to log
        """
        logging.getLogger(LOG_CHANNEL).info(msg)

    def log_warning(self, msg):
        """
        Log a warning

        :param msg: The warning message to log
        """
        logging.getLogger(LOG_CHANNEL).warning(msg)

    def log_error(self, msg):
        """
        Log an error

        :param msg: The error message to log
        """
        logging.getLogger(LOG_CHANNEL).error(msg)

    ################################################################################################################
    # Engine Bootstrap
    #

    def pre_dcc_launch_phase(self):
        """
        Special bootstrap method used to set up the Flame environment.
        This is designed to execute before Flame has launched, as part of the
        bootstrapping process.

        This method assumes that it is being executed inside a Flame python
        and is called from the app_launcher script which ensures such an environment.

        The bootstrapper will first import the wiretap API and setup other settings.

        It then attempts to execute the pre-DCC project creation process, utilizing
        both wiretap and QT (setup project UI) for this.

        Finally, it will return the command line args to pass to Flame as it is being
        launched.

        :returns: arguments to pass to the app launch process
        """
        if self.get_setting("debug_logging"):
            # enable Flame hooks debug
            os.environ["DL_DEBUG_PYTHON_HOOKS"] = "1"

        # see if we can launch into batch mode. We only do this when in a
        # shot context and if there is a published batch file in Shotgun
        #
        # For now, hard code the logic of how to detect which batch file to load up.
        # TODO: in the future, we may want to expose this in a hook - but it is arguably
        # pretty advanced customization :)
        #
        # Current logic: Find the latest batch publish belonging to the context

        if self.context.entity:
            # we have a current context to lock on to!

            # try to see if we can find the latest batch publish
            publish_type = sgtk.util.get_published_file_entity_type(self.sgtk)

            if publish_type == "PublishedFile":
                type_link_field = "published_file_type.PublishedFileType.code"
            else:
                type_link_field = "tank_type.TankType.code"

            sg_data = self.shotgun.find_one(publish_type,
                                            [[type_link_field, "is", self.get_setting("flame_batch_publish_type")],
                                             ["entity", "is", self.context.entity]],
                                            ["path"],
                                            order=[{"field_name": "created_at", "direction": "desc"}])

            if sg_data:
                # we have a batch file published for this context!
                batch_file_path = sg_data["path"]["local_path"]
                if os.path.exists(batch_file_path):
                    self.log_debug("Setting auto startup file '%s'" % batch_file_path)
                    os.environ["DL_BATCH_START_WITH_SETUP"] = batch_file_path

        # add Flame hooks for this engine
        flame_hooks_folder = os.path.join(self.disk_location, self.FLAME_HOOKS_FOLDER)
        sgtk.util.append_path_to_env_var("DL_PYTHON_HOOK_PATH", flame_hooks_folder)
        self.log_debug("Added to hook path: %s" % flame_hooks_folder)

        # now that we have a wiretap library, call out and initialize the project
        # automatically
        tk_flame = self.import_module("tk_flame")
        wiretap_handler = tk_flame.WiretapHandler()

        try:
            app_args = wiretap_handler.prepare_and_load_project()
        finally:
            wiretap_handler.close()

        return app_args

    def _define_qt_base(self):
        """
        Define QT behaviour. Subclassed from base class.
        """
        if self._engine_mode in (self.ENGINE_MODE_DCC, self.ENGINE_MODE_BACKBURNER):
            # We are running the engine inside of the Flame Application.
            # alternatively, we are running the engine in backburner
            #
            # in both these states, no special QT init is necessary.
            # Defer to default implementation which looks for pyside and
            # gracefully fails in case that isn't found.
            self.log_debug("Initializing default PySide for in-DCC / backburner use")
            return super(FlameEngine, self)._define_qt_base()

        else:
            # we are running the engine outside of Flame.
            # This is special - no QApplication is running at this point -
            # a state akin to running apps inside the shell engine.
            # We assume that in pre-launch mode, PySide is available since
            # we are running within the Flame python.
            from sgtk.platform import qt
            from sgtk.util.qt_importer import QtImporter

            importer = QtImporter()
            QtCore = importer.QtCore
            QtGui = importer.QtGui

            # a simple dialog proxy that pushes the window forward
            class ProxyDialogPySide(QtGui.QDialog):
                def show(self):
                    QtGui.QDialog.show(self)
                    self.activateWindow()
                    self.raise_()

                def exec_(self):
                    self.activateWindow()
                    self.raise_()
                    # the trick of activating + raising does not seem to be enough for
                    # modal dialogs. So force put them on top as well.
                    self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | self.windowFlags())
                    return QtGui.QDialog.exec_(self)

            base = {}
            base["qt_core"] = QtCore
            base["qt_gui"] = QtGui
            base["dialog_base"] = ProxyDialogPySide

            return base

    def cache_export_asset(self, asset_info):
        """
        Cache the export asset into the engine cache.

        :param asset_info: Information dictionary of the asset.
        See sg_export_hook.postExportAsset for details on the dictionary content.
        """

        # extract asset information
        sequence_name = asset_info.get("sequenceName")
        shot_name = asset_info.get("shotName")
        asset_type = asset_info.get("assetType")
        asset_name = asset_info.get("assetName")

        # reinitialize the export cache if the format doesn't fit the current asset
        if not isinstance(self._export_info, dict):
            self._export_info = {}

        if sequence_name not in self._export_info:
            self._export_info[sequence_name] = {shot_name: {asset_type: {asset_name: [asset_info]}}}

        elif shot_name not in self._export_info[sequence_name]:
            self._export_info[sequence_name][shot_name] = {asset_type: {asset_name: [asset_info]}}

        elif asset_type not in self._export_info[sequence_name][shot_name]:
            self._export_info[sequence_name][shot_name][asset_type] = {asset_name: [asset_info]}

        elif asset_name not in self._export_info[sequence_name][shot_name][asset_type]:
            self._export_info[sequence_name][shot_name][asset_type][asset_name] = [asset_info]
        else:
            self._export_info[sequence_name][shot_name][asset_type][asset_name].append(asset_info)

    def cache_batch_export_asset(self, info):
        """
        Cache the batch export asset into the engine cache.

        :param info: Information dictionary of the asset
                See sg_batch_hook.batchExportEnd for details on the dictionary content.
        """
        if not isinstance(self._export_info, list):
            self._export_info = []

        self._export_info.append(info)

    ################################################################################################################
    # export callbacks handling
    #
    # Any apps which are interested in registering custom exporters with Flame should use the methods
    # below. The register_export_hook() is called by apps in order to create a menu entry
    # on the Flame export menu. The remaining methods are used to call out from the actual Flame hook
    # to the relevant app code.
    #

    def register_export_hook(self, menu_caption, callbacks):
        """
        Allows an app to register an interest in one of the Flame export hooks.

        This is one of the interaction entry points in the system and this is how apps
        typically have their business logic executed. At app init, an app typically
        calls this method with a syntax like this:

            # set up callback map
            callbacks = {}
            callbacks["preCustomExport"] = self.pre_custom_export
            callbacks["preExportAsset"] = self.adjust_path
            callbacks["postExportAsset"] = self.register_post_asset_job

            # register with the engine
            self.engine.register_export_hook("Menu Caption", callbacks)

        The engine will keep track of things automatically, and whenever the user
        clicks the "Menu Caption" entry on the menu, the corresponding chain of callbacks
        will be called.

        All methods should have the following method signature:

            def export_callback(self, session_id, info)

        Where session_id is a unique session identifier (typically only used in advanced scenarios)
        and info reflects the info parameter passed from Flame (varies for different callbacks).

        For information which export can currently be registered against, see the
        flame_hooks/exportHook.py file.

        :param menu_caption: Text to appear on the Flame export menu
        :param callbacks: Dictionary of callbacks, see above for details.
        """
        if menu_caption in self._registered_export_instances:
            raise TankError("There is already a menu export preset named '%s'! "
                            "Please ensure your preset names are unique" % menu_caption)

        self.log_debug("Registered export preset '%s' with engine." % menu_caption)
        self._registered_export_instances[menu_caption] = callbacks

    def get_export_presets(self):
        """
        Internal engine method. Do not use outside of the engine.
        Returns all export presets registered by apps.

        :returns: List of preset titles
        """
        return self._registered_export_instances.keys()

    def create_export_session(self, preset_name):
        """
        Internal engine method. Do not use outside of the engine.
        Start a new export session.
        Creates a session object which represents a single export session in Flame.

        :param preset_name: The name of the preset which should be executed.
        :returns: session id string which is later passed into various methods
        """
        if preset_name not in self._registered_export_instances:
            raise TankError("The export preset '%s' is not registered with the current engine. "
                            "Current presets are: %s" % (preset_name, self._registered_export_instances.keys()))

        session_id = "tk_%s" % uuid.uuid4().hex

        # set up an export session
        self._export_sessions[session_id] = preset_name

        return session_id

    def trigger_export_callback(self, callback_name, session_id, info):
        """
        Internal engine method. Do not use outside of the engine.

        Dispatch method called from the various Flame hooks.
        This method will ensure that the Flame callbacks will be
        dispatched to the appropriate registered app callbacks.

        :param callback_name: Name of the Flame callback method
        :param session_id: Unique session identifier
        :param info: Metadata dictionary from Flame
        """
        self.log_debug("Flame engine export callback dispatch for %s" % callback_name)
        self.log_debug("Info parameters passed from Flame: %s" % pprint.pformat(info))

        if session_id not in self._export_sessions:
            self.log_debug("Ignoring request for unknown session %s..." % session_id)
            return

        # get the preset
        preset_name = self._export_sessions[session_id]
        tk_callbacks = self._registered_export_instances[preset_name]

        # call the callback in the preset
        if callback_name in tk_callbacks:
            # the app has registered interest in this!
            self.log_debug("Executing callback %s" % tk_callbacks[callback_name])
            tk_callbacks[callback_name](session_id, info)

    @property
    def export_info(self):
        """
        :return: Flame export cache
        """
        return self._export_info

    def clear_export_info(self):
        """
        Clear the Flame export cache
        """

        self._export_info = None

    ################################################################################################################
    # batch callbacks handling
    #
    # Any apps which are interested in register custom batch exporters with Flame should use the methods
    # below. The register_batch_hook() is called by apps in order to register an interest in pre and post
    # export callbacks when in batch mode. The Flame engine will ensure that the app's callbacks will get
    # called at the right time.
    #

    def register_batch_hook(self, callbacks):
        """
        Allows an app to register an interest in one of the Flame batch hooks.

        This one of the interaction entry points in the system and this is how apps
        typically have their business logic executed. At app init, an app typically
        calls this method with a syntax like this:

            # set up callback map
            callbacks = {}
            callbacks["batchExportBegin"] = self.before_export
            callbacks["batchExportEnd"] = self.after_export

            # register with the engine
            self.engine.register_batch_hook(callbacks)

        The engine will keep track of things automatically, and whenever a batch render executes,
        the corresponding chain of callbacks will be called.

        All methods should have the following method signature:

            def export_callback(self, info)

        For information which export can currently be registered against, see the
        flame_hooks/batchHook.py file.

        :param callbacks: Dictionary of callbacks, see above for details.
        """
        self.log_debug("Registered batch callbacks with engine: %s" % callbacks)
        self._registered_batch_instances.append(callbacks)

    def trigger_batch_callback(self, callback_name, info):
        """
        Internal engine method. Do not use outside of the engine.

        Dispatch method called from the various Flame hooks.
        This method will ensure that the Flame callbacks will be
        dispatched to the appropriate registered app callbacks.

        :param callback_name: Name of the Flame callback method
        :param session_id: Unique session identifier
        :param info: Metadata dictionary from Flame
        """
        self.log_debug("Flame engine batch callback dispatch for %s" % callback_name)
        self.log_debug("Info parameters passed from Flame: %s" % pprint.pformat(info))

        # dispatch to all callbacks
        for registered_batch_instance in self._registered_batch_instances:
            self.log_debug("Checking %s" % registered_batch_instance)
            if callback_name in registered_batch_instance:
                # the app has registered interest in this!
                self.log_debug("Executing callback %s" % registered_batch_instance[callback_name])
                registered_batch_instance[callback_name](info)

    ################################################################################################################
    # backburner integration
    #

    def get_server_hostname(self):
        """
        Return the hostname for the server which hosts this Flame setup.
        This is an accessor into the engine hook settings, allowing apps
        to query which host the closest Flame server is running on.

        :returns: hostname string
        """
        return self.execute_hook_method("project_startup_hook", "get_server_hostname")

    def get_backburner_tmp(self):
        """
        Return a location on disk, guaranteed to exist
        where temporary data can be put in such a way that
        it will be accessible for all backburner jobs, regardless of
        which host they execute on.

        :returns: path
        """
        return self.get_setting("backburner_shared_tmp")

    @property
    def _flame_exporter_supported(self):
        """
        :return True if Flame exporter API is supported.
        """

        # Note. Flame exporter can be used in 2019.1 but there are issues
        #       with transcoding of Movie files that prevent wide use of it
        #       with 2019.1.
        #
        return not self.is_version_less_than("2019.2")

    @property
    def transcoder(self):
        """
        :return transcoder: Transcoder to use to trancode a clip from
            one format to another.
        """

        if self._transcoder is not None:
            return self._transcoder

        tk_flame = self.import_module("tk_flame")

        if self._flame_exporter_supported:
            self._transcoder = tk_flame.Transcoder(
                engine=self
            )
        else:
            raise Exception("Transcoder not supported")

        return self._transcoder


    @property
    def thumbnail_generator(self):
        """
        :return thumbnail_generator: Thumbnail generator to use to generate
            thumbnail from Flame's asset published or rendered.
        """

        if self._thumbnail_generator is not None:
            return self._thumbnail_generator

        tk_flame = self.import_module("tk_flame")

        if self._flame_exporter_supported:
            self._thumbnail_generator = tk_flame.ThumbnailGeneratorFlame(
                engine=self
            )
        else:
            self._thumbnail_generator = tk_flame.ThumbnailGeneratorFFmpeg(
                engine=self
            )
        return self._thumbnail_generator

    @property
    def local_movie_generator(self):
        """
        :return local_movie_generator: Local movie generator to use to generate
            local movie file from Flame's asset published or rendered.
        """

        if self._local_movie_generator is not None:
            return self._local_movie_generator

        tk_flame = self.import_module("tk_flame")

        if self._flame_exporter_supported:
            self._thumbnail_generator = tk_flame.LocalMovieGeneratorFlame(
                engine=self
            )
        else:
            self._thumbnail_generator = tk_flame.LocalMovieGeneratorFFmpeg(
                engine=self
            )
        return self._thumbnail_generator

    def create_local_backburner_job(self, job_name, description, dependencies,
                                    instance, method_name, args, backburner_server_host=None):
        """
        Run a method in the local backburner queue.

        :param job_name: Name of the backburner job
        :param description: Description of the backburner job
        :param dependencies: None if the backburner job should execute arbitrarily. If you
                             want to set the job up so that it executes after another known task, pass
                             the backburner id or a list of ids here. This is typically used in conjunction with a postExportAsset
                             hook where the export task runs on backburner. In this case, the hook will return
                             the backburner id. By passing that id into this method, you can create a job which
                             only executes after the main export task has completed.
        :param instance: App or hook to remotely call up
        :param method_name: Name of method to remotely execute
        :param args: dictionary or args (**argv style) to pass to method at remote execution
        :param backburner_server_host: Name of the backburner server host.
        :return backburner_job_id: Id of the backburner job created
        """

        # the backburner executable

        backburner_job_cmd = os.path.join(self._install_root, "backburner", "cmdjob")

        # pass some args - most importantly tell it to run on the local host
        # looks like : chars are not valid so replace those
        backburner_args = []

        # run as current user, not as root
        backburner_args.append("-userRights")

        # attach the executable to the backburner job
        backburner_args.append("-attach")

        # increase the max task length to 600 minutes
        backburner_args.append("-timeout:600")

        # add basic job info
        # backburner does not do any kind of sanitaion itself, so ensure that job
        # info doesn't contain any strange characters etc

        # remove any non-trivial characters
        sanitized_job_name = re.sub(r"[^0-9a-zA-Z_\-,\. ]+", "_", job_name)
        sanitized_job_desc = re.sub(r"[^0-9a-zA-Z_\-,\. ]+", "_", description)

        # if the job name contains too many characters, backburner submission fails
        if len(sanitized_job_name) > 70:
            sanitized_job_name = "%s..." % sanitized_job_name[:67]
        if len(sanitized_job_desc) > 70:
            sanitized_job_desc = "%s..." % sanitized_job_desc[:67]

        # there is a convention in flame to append a time stamp to jobs
        # e.g. 'Export - XXX_YYY_ZZZ (10.02.04)
        sanitized_job_name += datetime.datetime.now().strftime(" (%H.%M.%S)")

        backburner_args.append("-jobName:\"%s\"" % sanitized_job_name)
        backburner_args.append("-description:\"%s\"" % sanitized_job_desc)

        # Specifying a remote backburner manager is only supported on 2016.1 and above
        if not self.is_version_less_than("2016.1"):
            bb_manager = self.get_setting("backburner_manager")
            if not bb_manager and not self.is_version_less_than("2018"):
                # No backburner manager speficied in settings. Ask local backburnerServer
                # which manager to choose from. (They might be none running locally)
                # Before 2018, you needed root privileges to execute this command.
                backburner_server_cmd = os.path.join(self._install_root, "backburner", "backburnerServer")
                bb_manager = subprocess.check_output([backburner_server_cmd, "-q", "MANAGER"])
                bb_manager = bb_manager.strip("\n")

            if bb_manager:
                backburner_args.append("-manager:\"%s\"" % bb_manager)

        # Set the server group to the backburner job
        bb_server_group = self.get_setting("backburner_server_group")
        if bb_server_group:
            backburner_args.append("-group:\"%s\"" % bb_server_group)

        # Specify the backburner server if provided
        if backburner_server_host:
            backburner_args.append("-servers:\"%s\"" % backburner_server_host)
        # Otherwise, fallback to the global backburner servers setting
        else:
            bb_servers = self.get_setting("backburner_servers")
            if bb_servers:
                backburner_args.append("-servers:\"%s\"" % bb_servers)

        # Set the backburner job dependencies
        if dependencies:
            if isinstance(dependencies, list):
                backburner_args.append("-dependencies:%s" % ",".join(dependencies)) 
            else:
                backburner_args.append("-dependencies:%s" % dependencies)

        # call the bootstrap script
        backburner_bootstrap = os.path.join(self.disk_location, "python", "startup", "backburner.py")

        # now we need to capture all of the environment and everything in a file
        # (thanks backburner!) so that we can replay it later when the task wakes up
        session_file = os.path.join(self.get_backburner_tmp(), "tk_backburner_%s.pickle" % uuid.uuid4().hex)

        data = {}
        data["engine_instance"] = self.instance_name
        data["serialized_context"] = sgtk.context.serialize(self.context)
        data["instance"] = instance if isinstance(instance, str) else instance.instance_name
        data["method_to_execute"] = method_name
        data["args"] = args
        data["sgtk_core_location"] = os.path.dirname(sgtk.__path__[0])
        data["flame_version"] = self._flame_version
        data["user_home"] = os.path.expanduser("~")
        fh = open(session_file, "wb")
        pickle.dump(data, fh)
        fh.close()

        full_cmd = "%s %s %s %s" % (backburner_job_cmd, " ".join(backburner_args), backburner_bootstrap, session_file)

        # On old Flame version, python hooks are running root. We need to run the command as the effective user to
        # ensure that backburner is running the job as the user who's using the Software to avoir permissions issues.
        if os.getuid() == 0:  # root
            # Getting the user name of the user who started Flame (the effective user)
            e_user = pwd.getpwuid(os.geteuid()).pw_name

            # Run the command as the effective user
            full_cmd = "sudo -u %s %s" % (e_user, full_cmd)
            self.log_debug("Running root but will send the job as [%s]" % e_user)

        try:
            # Make sure that the session is not expired
            sgtk.get_authenticated_user().refresh_credentials()
        except sgtk.authentication.AuthenticationCancelled:
            self.log_debug("User cancelled auth. No backburner job will be created.")
        else:
            self.log_debug("Starting backburner job '%s'" % job_name)
            self.log_debug("Command line: %s" % full_cmd)
            self.log_debug("App: %s" % instance)
            self.log_debug("Method: %s with args %s" % (method_name, args))

            # kick it off
            backburner_job_submission = subprocess.Popen([full_cmd], stdout=subprocess.PIPE, shell=True)
            stdout, stderr = backburner_job_submission.communicate()

            self.log_debug(stdout)

            job_id_regex = re.compile(r"(?<=Successfully submitted job )(\d+)")
            match = job_id_regex.search(stdout)

            if match:
                backburner_job_id = match.group(0)
                self.log_debug("Backburner job created (%s)" % backburner_job_id)
                return backburner_job_id

            else:
                error = ["Shotgun backburner job could not be created."]
                if stderr:
                    error += ["Reason: " + stderr]
                error += ["See backburner logs for details."]

                raise TankError("\n".join(error))

    ################################################################################################################
    # accessors to various core settings and functions

    def __get_wiretap_central_binary(self, binary_name):
        """
        Try to returns the path to a binary in the Wiretap Central binary collection.

        This function is compatible with both new Wiretap Central and the legacy Wiretap Central.

        :param binary_name: Name of desired binary
        :returns: Absolute path as a string
        """
        # Wiretap Central can only be present on MacOS and on Linux
        if sys.platform not in ["darwin", "linux2"]:
            raise TankError("Your operating system does not support Wiretap Central!")

        # Priority have to be given to every ".bin" executable on the Wiretap Central binary folder
        wtc_path = self._get_wiretap_central_bin_path()
        binary = os.path.join(wtc_path, binary_name + ".bin")
        if os.path.exists(binary):
            return binary

        # If not found, we should look for the same path without the ".bin"
        binary = os.path.join(wtc_path, binary_name)
        if os.path.exists(binary):
            return binary

        # If we reach this, we are running a legacy Wiretap Central
        wtc_path = self._get_wiretap_central_legacy_bin_path()
        binary = os.path.join(wtc_path, binary_name)
        if os.path.exists(binary):
            return binary

        # We don't have any Wiretap Central installed on this workstation
        raise TankError("Cannot find binary '%s'!" % binary_name)

    def _get_wiretap_central_bin_path(self):
        """
        Get the path to the Wiretap Central binaries folder based on the current operating system.

        :return: Path to the Wiretap Central binaries folder
        """
        if sys.platform == "darwin":
            return "/Library/WebServer/Documents/WiretapCentral/cgi-bin"
        elif sys.platform == "linux2":
            return "/var/www/html/WiretapCentral/cgi-bin"

    def _get_wiretap_central_legacy_bin_path(self):
        """
        Get the path to the legacy Wiretap Central binaries folder based on the current operating system.

        :return: Path to the legacy Wiretap Central binaries folder
        """
        if sys.platform == "darwin":
            return "/Library/WebServer/CGI-Executables/WiretapCentral"
        elif sys.platform == "linux2":
            return "/var/www/cgi-bin/WiretapCentral"

    def get_ffmpeg_path(self):
        """
        Returns the path to the ffmpeg executable that ships with Flame.

        :returns: Absolute path as a string
        """
        return self.__get_wiretap_central_binary("ffmpeg")

    def get_read_frame_path(self):
        """
        Returns the path to the read_frame utility that ships with Flame.

        :returns: Absolute path as a string
        """
        return self.__get_wiretap_central_binary("read_frame")


def sgtk_exception_trap(ex_cls, ex, tb):
    """
    UI Popup and logging exception trap override.

    This method is used to override the default exception reporting behaviour
    inside the embedded Flame python interpreter to make errors more visible
    to the user.

    It attempts to create a QT messagebox with a formatted error message to
    alert the user that something has gong wrong. In addition to this, the
    default exception handling is also carried out and the exception is also
    written to the log.

    Note that this is a global object and not an engine-relative thing, so that
    the exception handler will operate correctly even if the engine instance no
    longer exists.
    """
    # careful about infinite loops here - we mustn't raise exceptions.

    # like in other environments and scripts, for TankErrors, we assume that the
    # error message is already a nice descriptive, crafted message and try to present
    # this in a user friendly fashion
    #
    # for other exception types, we give a full call stack.

    error_message = "Critical: Could not format error message."

    try:
        traceback_str = "\n".join(traceback.format_tb(tb))
        if ex_cls == TankError:
            # for TankErrors, we don't show the whole stack trace
            error_message = "A Shotgun error was reported:\n\n%s" % ex
        else:
            error_message = "A Shotgun error was reported:\n\n%s (%s)\n\nTraceback:\n%s" % (ex, ex_cls, traceback_str)
    except:
        pass

    # now try to output it
    try:
        from sgtk.platform.qt import QtGui, QtCore
        if QtCore.QCoreApplication.instance():
            # there is an application running - so pop up a message!
            QtGui.QMessageBox.critical(None, "Shotgun General Error", error_message)
    except:
        pass

    # and try to log it
    try:
        error_message = "An exception was raised:\n\n%s (%s)\n\nTraceback:\n%s" % (ex, ex_cls, traceback_str)
        logging.getLogger(LOG_CHANNEL).error(error_message)
    except:
        pass

    # in addition to the ui popup, also defer to the default mechanism
    sys.__excepthook__(type, ex, tb)
