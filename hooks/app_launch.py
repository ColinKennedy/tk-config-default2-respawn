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
import imp
import sys
import os

# IMPORT THIRD-PARTY LIBRARIES
# This sys.path.append adds `rezzurect`
_CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
_SHOTGUN_CONFIG_ROOT = os.path.dirname(_CURRENT_DIR)
sys.path.append(os.path.join(_SHOTGUN_CONFIG_ROOT, 'vendors'))

# Now we add `rez` so that `rezzurect` can import and use it
# TODO : Remove this sys.path.append later for something better
sys.path.append(r'C:\Users\korinkite\rez\Lib\site-packages\rez-2.22.1-py2.7.egg')
sys.path.append(r'C:\Users\selecaotwo\rez2\Lib\site-packages\rez-2.22.1-py2.7.egg')

# TODO : Make this chooser import more concise (bring to the root folder)
from rezzurect.adapters import chooser
from rezzurect import environment

import tank


_REZ_PACKAGE_ROOT = os.path.join(_SHOTGUN_CONFIG_ROOT, 'rez_packages')

ENGINES_TO_PACKAGE = {
    'tk-houdini': 'houdini',
    'tk-maya': 'maya',
    'tk-nuke': 'nuke',
}
PACKAGE_TO_REZ_REPO = {
    'nuke': 'rez-nuke',
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
        init_config()

        package = ENGINES_TO_PACKAGE[engine_name]
        runner = get_runner(platform.system())

        if not package:
            self.logger.debug('No rez package was found. The default boot, instead.')
            return run_with_os(runner, app_path, app_args)

        rez_package_name = PACKAGE_TO_REZ_REPO[package]
        return run_with_rez(rez_package_name, package, version, runner, app_args)


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

        process = context.execute_command(command)

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


def _get_config_root_directory():
    '''str: Get the absolute path of this Shotgun Pipeline configuration.'''
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def is_config_valid(path):
    '''bool: Check if the given path is a rezconfig file.'''
    return os.path.isfile(path) and os.stat(path).st_size != 0


def init_config():
    '''Get this Pipeline Configuration's Rez config file and add it.'''
    config_file = get_config_path()
    os.environ['REZ_CONFIG_FILE'] = config_file


def run_with_os(runner, app_path, app_args):
    command = runner.get_command(app_path, app_args)
    return_code = os.system(command)
    return {'command': command, 'return_code': return_code}


def run_with_rez(repo_name, package_name, version, runner, app_args):
    '''Execute a repository packages main command.

    Args:
        repo_name (str):
            The name of the rez package folder on-disk. This is not necessarily
            the same name as `package_name` though it can be.
        package_name (str):
            The name of the installed rez package. This is the "name"
            variable defned in `repo_name`/{version}/package.py file.
        version (str):
            The specific install of the installed rez package. This is the "version"
            variable defned in `repo_name`/{version}/package.py file.
        runner (`BaseAdapter`):
            The class used to actually run the command in the user's Rez package.
        app_args (str):
            Any arguments the application may require

    Raises:
        EnvironmentError: If the Rez installation could not be found.
        RuntimeError: If the package could not be built or install.

    '''
    def get_context(packages):
        try:
            return resolved_context.ResolvedContext(packages)
        except exceptions.PackageFamilyNotFoundError:
            return

    try:
        import rez as _  # pylint: disable=W0611
    except ImportError:
        # If the user doesn't have rez installed properly, try to add it ourselves
        rez_path = runner.get_rez_module_root()

        if not rez_path:
            raise EnvironmentError('rez is not installed and could not be automatically found. Cannot continue.')

        sys.path.append(rez_path)

    from rez import resolved_context
    from rez import exceptions
    from rez import config

    source_path = os.path.join(_REZ_PACKAGE_ROOT, repo_name, version)
    if not os.path.isdir(source_path):
        raise RuntimeError('Path "{source_path}" could not be found.'.format(source_path=source_path))

    try:
        package_module = imp.load_source(
            'rez_{repo_name}_definition'.format(repo_name=repo_name),
            os.path.join(source_path, 'package.py'),
        )
    except ImportError:
        raise RuntimeError('source_path "{source_path}" has no package.py file.'.format(
            source_path=source_path))

    packages = ['{package_module.name}-{version}'.format(
        package_module=package_module, version=version)]
    context = get_context(packages)

    if context:
        return runner.execute(package_name, version, context, app_args)

    # If we get this far, it means that the context failed to resolve. This
    # happens commonly for 2 reasons
    # 1. The Rez package was never built and needs to be built.
    # 2. `package` does not have a Rez package definition.
    # If the issue is #2, error out. But if it's #1, try to build the package now
    #
    build_path = os.path.join(source_path, 'build')

    install_path = os.path.join(
        config.config.get('local_packages_path'),
        package_module.name,
        version,
        package_module.install_root,
    )

    environment.init(package_name, version, source_path, build_path, install_path)

    builder = chooser.get_adapter(package_name, version)
    builder.make_package(package_module)

    # The package hopefully is now built. Lets get that context again
    context = get_context(packages)

    if not context:
        raise RuntimeError('The package "{packages}" could not be found or built. '.format(packages=packages))

    return runner.execute(package_name, version, context, app_args)


def get_runner(system=''):
    '''Get an runner for the given OS.

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


def get_config_path():
    '''str: Get the absolute path to this Pipeline Configuration's Rez config file.'''
    return os.path.join(_get_config_root_directory(), 'rez_packages', '.rezconfig')
