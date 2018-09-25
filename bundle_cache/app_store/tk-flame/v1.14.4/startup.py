# Copyright (c) 2016 Shotgun Software Inc.
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
import re

import sgtk
from sgtk import TankError
from sgtk.platform import SoftwareLauncher, SoftwareVersion, LaunchInformation


class FlameLauncher(SoftwareLauncher):
    """
    Handles launching Flame executables. Automatically starts up a tk-flame
    engine with the current context in the new session of Houdini.
    """

    # A lookup to map an executable name to a product. This is critical for
    # linux where the product does not show up in the path.
    EXECUTABLE_TO_PRODUCT = {
        "flame": "Flame",
        "flameassist": "Flame Assist",
        "flare": "Flare",
        "flamepremium": "Flame Premium",
    }

    # lookup for icons
    ICON_LOOKUP = {
        "Flame": "icon_256.png",
        "Flame Assist": "flame_assist_icon_256.png",
        "Flare": "flare_icon_256.png",
        "Flame Premium": "icon_256.png"
    }

    # Named regex strings to insert into the executable template paths when
    # matching against supplied versions and products. Similar to the glob
    # strings, these allow us to alter the regex matching for any of the
    # variable components of the path in one place
    COMPONENT_REGEX_LOOKUP = {
        "darwin": {
            "version": "\d.*",  # starts with a number followed by anything
            "executable": "[\w]+",  # word characters (a-z0-9)
        },
        "linux2": {
            "version": "\d.*",  # starts with a number followed by anything
            "executable": "[\w]+",  # word characters (a-z0-9)
        }
    }

    # This dictionary defines a list of executable template strings for each
    # of the supported operating systems. The templates are used for both
    # globbing and regex matches by replacing the named format placeholders
    # with an appropriate glob or regex string.
    EXECUTABLE_TEMPLATES = {
        "darwin": [
            "/opt/Autodesk/{executable}_{version}/bin/startApplication",
        ],
        "linux2": [
            # /usr/discreet/flame_2017.1/bin/startApplication
            # /usr/discreet/flameassist_2017.1.pr70/bin/startApplication
            # /usr/discreet/flare_2017.1/bin/startApplication
            # /usr/discreet/flamepremium_2017.1/bin/startApplication
            "/usr/discreet/{executable}_{version}/bin/startApplication",
            "/opt/Autodesk/{executable}_{version}/bin/startApplication",
        ]
    }

    @property
    def minimum_supported_version(self):
        """
        The minimum supported Flame version.
        """
        # 2018 was the first version of flame that shipped with taap included.
        return "2018"

    def prepare_launch(self, exec_path, args, file_to_open=None):
        """
        Prepares the given software for launch

        :param str exec_path: Path to DCC executable to launch
        :param str args: Command line arguments as strings
        :param str file_to_open: (optional) Full path name of a file to open on
            launch

        :returns: :class:`LaunchInformation` instance
        """
        use_builtin_plugin = self.get_setting("use_builtin_plugin")

        # If there is a plugin to launch with, we don't have much in the
        # way of prep work to do.
        if use_builtin_plugin:
            # flame comes with toolkit built-in, so no need to
            # run any startup logic.
            self.logger.debug("Using the builtin plugin on Flame launch.")
            env = {
                "SHOTGUN_SITE": self.sgtk.shotgun_url,
                "SHOTGUN_ENTITY_ID": str(self.context.project["id"]),
                "SHOTGUN_ENTITY_TYPE": str(self.context.project["type"]),
                "SHOTGUN_ENTITY_NAME": str(self.context.project["name"])
            }
        else:
            self.logger.debug("Using the legacy bootstrap on Flame launch.")

            # We have a list of environment variables that we need to
            # gather and return. These are various bits of data that
            # the python/startup/app_launcher.py script uses during
            # its bootstrapping of SGTK during launch.
            env = {
                "TOOLKIT_ENGINE_NAME": self.engine_name,
                "TOOLKIT_CONTEXT": sgtk.context.serialize(self.context)
            }

            # We also need to store the various components of the Flame
            # version in the environment. The app_launcher.py script that
            # launches and bootstraps SGTK registers these with the engine,
            # and the engine then logs metrics about what version of Flame
            # has been launched.
            #
            # The exec_path is likely a path to the .app that will be launched.
            # What we need instead of is the fully-qualified path to the Flame
            # startApplication executable, which is what we'll extract the
            # version components from. Examples of what this path can be and
            # how it's parsed can be found in the docstring of _get_flame_version
            # method.
            self.logger.debug("Flame app executable: %s", exec_path)
            if exec_path.endswith(".app"):
                # The flame executable contained withing the .app will be a
                # symlink to the startApplication path we're interested in.
                flame_path = os.path.join(exec_path, "Contents", "MacOS", "flame")
                app_path = os.path.realpath(flame_path)
            else:
                app_path = os.path.realpath(exec_path)

            if app_path != exec_path:
                self.logger.debug(
                    "Flame app executable has been flattened. The flattened "
                    "path that will be parsed and used at launch time is: %s",
                    app_path
                )

            self.logger.debug("Parsing Flame (%s) to determine Flame version...", app_path)
            major, minor, patch, version_str = self._get_flame_version(app_path)
            self.logger.debug("Found Flame version: %s", version_str)

            env.update(
                dict(
                    TOOLKIT_FLAME_VERSION=version_str,
                    TOOLKIT_FLAME_MAJOR_VERSION=str(major),
                    TOOLKIT_FLAME_MINOR_VERSION=str(minor),
                    TOOLKIT_FLAME_PATCH_VERSION=str(patch),
                )
            )

            # The install root of Flame is also used by the app_launcher
            # script, which registers it with the engine after bootstrapping.
            # The path is used by the engine when submitting render jobs
            # to Backburner.
            match = re.search("(^.*)/(fla[mr]e[^_]*_[^/]+)/bin", app_path)
            if match:
                env["TOOLKIT_FLAME_INSTALL_ROOT"] = match.group(1)
                app_folder = match.group(2)
                wiretap_path = os.path.join(
                    env["TOOLKIT_FLAME_INSTALL_ROOT"],
                    app_folder,
                    "python",
                )
                self.logger.debug("Adding wiretap root path to PYTHONPATH: %s", wiretap_path)
                sgtk.util.prepend_path_to_env_var("PYTHONPATH", wiretap_path)
            else:
                raise TankError(
                    "Cannot extract install root from the path: %s" % app_path
                )

            # The Python executable bundled with Flame is used by the engine
            # when submitting Backburner jobs.
            env["TOOLKIT_FLAME_PYTHON_BINARY"] = "%s/python/%s/bin/python" % (
                env["TOOLKIT_FLAME_INSTALL_ROOT"],
                version_str
            )

            # We need to override the exec_path and args that will be used
            # to launch Flame. We launch using the Python bundled with Flame
            # and the app_launcher.py script bundled with the engine. That
            # app_launcher script will do some prep work prior to launching
            # Flame itself.
            #
            # <flame python> <tk-flame>/python/startup/app_launcher.py dcc_path dcc_args
            #
            launch_script = os.path.join(
                os.path.dirname(__file__),
                "python",
                "startup",
                "app_launcher.py",
            )
            exec_path = env["TOOLKIT_FLAME_PYTHON_BINARY"]
            args = "'%s' %s %s" % (launch_script, app_path, args)

        return LaunchInformation(exec_path, args, env)

    def scan_software(self):
        """
        Scan the filesystem for flame executables.

        :return: A list of :class:`SoftwareVersion` objects.
        """

        self.logger.debug("Scanning for Flame executables...")

        supported_sw_versions = []
        for sw_version in self._find_software():
            (supported, reason) = self._is_supported(sw_version)
            if supported:
                supported_sw_versions.append(sw_version)
            else:
                self.logger.debug(
                    "SoftwareVersion %s is not supported: %s" %
                    (sw_version, reason)
                )

        return supported_sw_versions

    def _find_software(self):

        # all the executable templates for the current OS
        executable_templates = self.EXECUTABLE_TEMPLATES.get(sys.platform, [])
        executable_regexp = self.COMPONENT_REGEX_LOOKUP.get(sys.platform, [])

        # all the discovered executables
        sw_versions = []

        for executable_template in executable_templates:

            self.logger.debug("Processing template %s.", executable_template)

            executable_matches = self._glob_and_match(
                executable_template,
                executable_regexp
            )

            # Extract all products from that executable.
            for (executable_path, key_dict) in executable_matches:

                # extract the matched keys form the key_dict (default to None if
                # not included)
                executable_version = key_dict.get("version")
                executable_product = key_dict.get("product")
                executable_name = key_dict.get("executable")
                executable_app = key_dict.get("app")

                # we need a product to match against. If that isn't provided,
                # then an executable name should be available. We can map that
                # to the proper product.
                if not executable_product:
                    executable_product = \
                        self.EXECUTABLE_TO_PRODUCT.get(executable_name)

                # Unknown product
                if not executable_product:
                    continue

                # Adapt the FlameAssist product name
                if executable_product == "FlameAssist":
                    executable_product = "Flame Assist"

                # only include the products that are covered in the EXECUTABLE_TO_PRODUCT dict
                if not executable_product.startswith("Flame") and not executable_product.startswith("Flare"):
                    self.logger.debug(
                        "Product '%s' is unrecognized. Skipping." %
                        (executable_product,)
                    )
                    continue

                # exclude Technology demo apps
                if executable_app and "Technology Demo" in executable_app:
                    self.logger.debug(
                        "Ignoring '%s %s - %s'" %
                        (executable_product, executable_version, executable_app)
                    )
                    continue

                # figure out which icon to use
                icon_path = os.path.join(
                    self.disk_location,
                    self.ICON_LOOKUP.get(executable_product, self.ICON_LOOKUP["Flame"])
                )
                self.logger.debug("Using icon path: %s" % (icon_path,))

                sw_versions.append(
                    SoftwareVersion(
                        executable_version,
                        executable_product,
                        executable_path,
                        icon_path
                    )
                )

        return sw_versions

    def _get_flame_version(self, flame_path):
        """
        Returns the version string for the given Flame path
        
        <INSTALL_ROOT>/flameassist_2016.2/bin/startApplication        --> (2016, 2, 0, "2016.2")
        <INSTALL_ROOT>/flameassist_2016.3/bin/startApplication        --> (2016, 3, 0, "2016.3")
        <INSTALL_ROOT>/flameassist_2016.0.3.322/bin/startApplication  --> (2016, 0, 3, "2016.0.3.322")
        <INSTALL_ROOT>/flameassist_2016.2.pr99/bin/startApplication   --> (2016, 2, 0, "2016.2.pr99")
        <INSTALL_ROOT>/flame_2016.pr50/bin/start_Flame                --> (2016, 0, 0, "2016.pr50")

        If the patch, minor or major version cannot be extracted, it will be set to zero.

        :param flame_path: path to executable
        :returns: (major, minor, patch, full_str)
        """

        # do a quick check to ensure that we are running 2015.2 or later
        re_match = re.search("/fla[mr]e[^_]*_([^/]+)/bin", flame_path)
        if not re_match:
            raise TankError("Cannot extract Flame version number from the path '%s'!" % flame_path)
        version_str = re_match.group(1)

        # Examples:
        # 2016
        # 2016.2
        # 2016.pr99
        # 2015.2.pr99

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

        return (major_ver, minor_ver, patch_ver, version_str)
