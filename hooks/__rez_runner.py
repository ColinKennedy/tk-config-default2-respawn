#!/usr/bin/env python
#

# IMPORT STANDARD LIBRARIES
import subprocess
import platform

# IMPORT THIRD-PARTY LIBRARIES
# TODO : Make this chooser import more concise (bring to the root folder)
from rezzurect.adapters import chooser


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
    def get_rez_module_root(cls):
        '''str: Get the absolute path to where the rez module is located.'''
        # TODO : Remove this return statement, later
        return '/usr/lib/python2.7/site-packages/rez-2.22.1-py2.7.egg'
        command = cls.get_rez_root_command()
        module_path, stderr = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()

        module_path = module_path.strip()

        if not stderr and module_path:
            return module_path

        return ''

    @classmethod
    def execute(cls, package, version, context, args):
        '''Run the context's main command with the given `args`.

        Args:
            package (str): The name of the installed Rez package to run.
            version (str): The specific instance of `package` to run.
            context (`rez.resolved_context.ResolvedContext`): The context to run "main".
            args (str): Additional arguments to add to the generated command.

        Returns:
            dict[str, str or int]: The results of the command's execution.

        '''
        # Note: For the package to be valid, it must expose a "main" command.
        setting_adapter = chooser.get_setting_adapter(package, version)
        command = setting_adapter.get_executable_command()

        if args:
            command += ' {args}'.format(args=args)

        process = context.execute_shell(
            command=command,
            stdin=False,
            block=False,
        )

        return_code = process.wait()
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


def get_runner(system=''):
    '''Get an adapter which runs the Rez command for the given OS.

    Args:
        system (`str`, optional):
            The OS to use. If no OS is given, the user's current OS is used, instead.
            Default: "".

    Raises:
        NotImplementedError: If the given `system` has no runner.

    Returns:
        `BaseAdapter`: The found runner, if any.

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
