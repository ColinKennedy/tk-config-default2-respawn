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
import os

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

    '''An adapter that abstracts the different OS-specific syntaxes for running commands.

    Attributes:
        shell_type (str): The shell which Rez will use to call the "main" command.

    '''

    shell_type = 'bash'

    @staticmethod
    def get_command(path, args):
        '''Create a command to run the given path, for Linux.

        Note:
            This function runs in the user's background.

        Args:
            path (str): The full or relative path to the executable to make into a command.
            args (str): Every argument to add to the generated command.

        Returns:
            str: The generated command.

        '''
        # Note: Execute the command in the background
        return '"{path}" {args} &'.format(path=path, args=args)

    @staticmethod
    def get_rez_root_command():
        '''str: Print the location where rez is installed (if it is installed).'''
        return 'rez-env rez -- printenv REZ_REZ_ROOT'

    @classmethod
    def execute(cls, context, args):
        '''Run the context's main command with the given `args`.

        Args:
            context (`rez.resolved_context.ResolvedContext`): The context to run "main".
            args (str): Every argument to add to the generated command.

        Returns:
            dict[str, str or int]: The results of the command's execution.

        '''
        # Note: For the package to be valid, it must expose a "main" command.
        command = 'main'

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

    '''An adapter that abstracts Linux commands and Rez.'''

    pass


class WindowsAdapter(BaseAdapter):

    '''An adapter that abstracts Linux commands and Rez.

    Attributes:
        shell_type (str): The shell which Rez will use to call the "main" command.

    '''

    shell_type = 'cmd'

    @staticmethod
    def get_command(path, args):
        '''Create a command to run the given path, for Linux.

        Note:
            This function runs in the user's background.

        Args:
            path (str): The full or relative path to the executable to make into a command.
            args (str): Every argument to add to the generated command.

        Returns:
            str: The generated command.

        '''
        # Note: We use the "start" command to avoid any command shells from
        # popping up as part of the application launch process.
        #
        return 'start /B "App" "{path}" {args}'.format(path=path, args=args)

    @staticmethod
    def get_rez_root_command():
        '''str: Print the location where rez is installed (if it is installed).'''
        return 'rez-env rez -- echo %REZ_REZ_ROOT%'


def get_adapter(system=''):
    '''Get an adapter for the given OS.

    Args:
        system (`str`, optional):
            The OS to use. If no OS is given, the user's current OS is used, instead.
            Default: "".

    Raises:
        NotImplementedError: If the given `system` has no adapter.

    Returns:
        `BaseAdapter`: The found adapter, if any.

    '''
    if not system:
        system = platform.system()

    options = {
        'Linux': LinuxAdapter,
        'Windows': WindowsAdapter,
    }

    try:
        return options[system]
    except KeyError:
        raise NotImplementedError('system "{system}" is currently unsupported. Options were, "{options}"'
                                  ''.format(system=system, options=list(options)))
