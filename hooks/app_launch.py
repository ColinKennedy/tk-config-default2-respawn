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
import subprocess
import platform
import sys
import os
import re

# IMPORT THIRD-PARTY LIBRARIES
from rez import resolved_context
import tank


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
        multi_launchapp = self.parent
        extra = multi_launchapp.get_setting('extra')

        adapter = get_adapter(platform.system())
        packages = adapter.get_packages(engine_name)

        if not packages:
            self.logger.debug('No rez packages were found. The default boot, instead.')
            command = adapter.get_command(app_path, app_args)
            return_code = os.system(command)
            return {'command': command, 'return_code': return_code}

        context = resolved_context.ResolvedContext(packages)
        return adapter.execute(context, app_args)


class BaseAdapter(object):

    shell_type = 'bash'
    # TODO : This should be define-able in a YAML file. There's no reason why it should exist here
    engines = {
        'tk-nuke': ('nuke', ),
    }

    @staticmethod
    def get_command(path, args):
        # Note: Execute the command in the background
        return '{path} {args} &'.format(path=path, args=args)

    @classmethod
    def get_packages(cls, name):
        return cls.engines.get(name, tuple())

    @staticmethod
    def get_rez_root_command():
        return 'rez-env rez -- printenv REZ_REZ_ROOT'

    @classmethod
    def execute(cls, context, args):
        command = 'Nuke11.2'

        if args:
            command += ' {args}'.format(args=args)

        proc = context.execute_shell(
            command=command,
            parent_environ=os.environ.copy(),
            shell=cls.shell_type,
            stdin=False,
            block=False
        )

        return_code = proc.wait()
        context.print_info(verbosity=True)

        return {
            'command': command,
            'return_code': return_code,
        }



class LinuxAdapter(BaseAdapter):
    pass


class WindowsAdapter(BaseAdapter):

    shell_type = 'cmd'

    @staticmethod
    def get_command(path, args):
        # Note: We use the "start" command to avoid any command shells from
        # popping up as part of the application launch process.
        #
        return 'start /B "App" "{path}" {args}'.format(path=path, args=args)

    @staticmethod
    def get_rez_root_command():
        return 'rez-env rez -- echo %REZ_REZ_ROOT%'


def get_adapter(system=''):
    if not system:
        system = platform.system()

    options = {
        'Linux': LinuxAdapter,
        'Windows': WindowsAdapter,
    }

    try:
        return options[system]
    except KeyError:
        raise EnvironmentError('system "{system}" is currently unsupported.'.format(system=system))
