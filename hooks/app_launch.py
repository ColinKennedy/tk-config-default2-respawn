# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
App Launch Hook

This hook is executed to launch the applications.
"""

# IMPORT STANDARD LIBRARIES
import platform
import imp
import sys
import os

# IMPORT THIRD-PARTY LIBRARIES
import tank


__CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
rez_config = imp.load_source('rez_config', os.path.join(__CURRENT_DIR, '__rez_config.py'))
rez_launcher = imp.load_source('rez_launcher', os.path.join(__CURRENT_DIR, '__rez_launcher.py'))
rez_runner = imp.load_source('rez_runner', os.path.join(__CURRENT_DIR, '__rez_runner.py'))


ENGINES_TO_PACKAGE = {
    'tk-houdini': 'houdini',
    'tk-maya': 'maya',
    'tk-nuke': 'nuke',
}


class AppLaunch(tank.Hook):
    """
    Hook to run an application.
    """

    def execute(self, app_path, app_args, version, engine_name, **kwargs):
        """
        The execute functon of the hook will be called to start the required application

        :param app_path: (str) The path of the application executable
        :param app_args: (str) Any arguments the application may require
        :param version: (str) version of the application being run if set in the
            "versions" settings of the Launcher instance, otherwise None
        :param engine_name (str) The name of the engine associated with the
            software about to be launched.

        :returns: (dict) The two valid keys are 'command' (str) and 'return_code' (int).
        """
        rez_config.init_config()

        package = ENGINES_TO_PACKAGE[engine_name]
        runner = rez_runner.get_runner(platform.system())

        if not package:
            self.logger.debug('No rez package was found. The default boot, instead.')
            return run_with_os(runner, app_path, app_args)

        return rez_launcher.run_with_rez(package, version, runner, app_args)


def run_with_os(runner, app_path, app_args):
    command = runner.get_command(app_path, app_args)
    return_code = os.system(command)
    return {'command': command, 'return_code': return_code}
