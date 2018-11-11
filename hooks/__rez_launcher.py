#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO: It's entirely possible that Rez is able to do what this module does already.
#       I just couldn't find any documentation / code that suggested this.
#       In the future, if a better method is found, feel free to replace this.
#
'''The module that is responsible for building and running Rez packages.

This module uses the "package.py" file located in each Rez package definition to
recursively build the package's requirements.

'''

# IMPORT STANDARD LIBRARIES
import logging
import imp
import sys
import os

# IMPORT THIRD-PARTY LIBRARIES
from rezzurect.utils import rezzurect_config
from rezzurect import environment

# TODO : Move rez package imports out of functions and up at the top, instead

_CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
_SHOTGUN_CONFIG_ROOT = os.path.dirname(_CURRENT_DIR)
LOGGER = logging.getLogger('rezzurect.rez_launcher')


def _get_context(packages):
    '''Get a Rez environment that satisfies the given packages, if possible.

    Args:
        packages (list[str]):
            All of the packages that must be contained in the context.
            It can include the name-version of the package
            or just the package name. Example: ["nuke-11.2v3"] or ["nuke"].

    Returns:
        `resolved_context.ResolvedContext` or NoneType:
            The found package countext, assuming `packages`
            has already been built correctly.

    '''
    from rez import resolved_context
    from rezzurect import manager

    try:
        return resolved_context.ResolvedContext(packages)
    except manager.PACKAGE_EXCEPTIONS:
        return


def add_rez_to_sys_path_if_needed(runner):
    '''Make sure that Rez is importable on the user's system.

    Raises:
        EnvironmentError: If Rez is not importable and we could not find rez, ourselves.

    '''
    try:
        import rez as _  # pylint: disable=W0611
    except ImportError:
        # If the user doesn't have rez sourced in the PYTHONPATH but it is installed
        # then lets try to add it ourselves
        #
        rez_path = runner.get_rez_module_root()

        if not rez_path:
            raise EnvironmentError('rez is not installed and could not be automatically found. Cannot continue.')

        sys.path.append(rez_path)


def get_package_module(source_path, name):
    '''Import the package.py file as a Python module and return it.

    Args:
        source_path (str): The absolute path to where the package/version files exist.
        name (str): The name which will be used as a namespace for the imported module.

    Returns:
        module or NoneType: The imported module, if it could be found.

    '''
    try:
        return imp.load_source(
            'rez_{name}_definition'.format(name=name),
            os.path.join(source_path, 'package.py'),
        )
    except ImportError:
        return


def get_context(packages):
    '''Get a Rez environment that satisfies the given packages, if possible.

    Args:
        packages (list[str]):
            All of the packages that must be contained in the context.
            It can include the name-version of the package
            or just the package name. Example: ["nuke-11.2v3"] or ["nuke"].

    Raises:
        EnvironmentError:
            If the given packages have one or more missing package.py
            (which indicates an incomplete package build).

    Returns:
        `resolved_context.ResolvedContext`: The found package countext.

    '''
    from rezzurect import manager

    try:
        return _get_context(packages)
    except manager.PACKAGE_EXCEPTIONS:
        raise EnvironmentError(
            'Packages "{packages}" were installed incorrectly. Please contact '
            'an administrator to fix this.'.format(packages=packages))


def build_context_from_scratch(package, version, root, source_path=''):
    '''Build the given `package` recursively.

    Note:
        This function assumes that `package` has not been built before.
        "Partial" building is not supported and old files will be overwritten.

    Args:
        package (str):
            The name of the Rez package to build.
        version (str):
            The specific release of `package` to build.
        root (str):
            The absolute path to where all Rez packages can be found.
        source_path (str, optional):
            The absolute path to where the package.py file exists.
            If no path is given, assume that the source_path can be found
            under `root`. Default: "".

    Raises:
        ValueError: If `source_path` was not given and could not be found.

    '''
    from rezzurect.utils import rezzurect_config
    from rezzurect import manager
    from rez import config

    if not source_path:
        source_path = os.path.join(root, package, version)

        if not os.path.isfile(os.path.join(source_path, 'package.py')):
            raise ValueError('source_path could not be found.')

    # TODO : Using `config_package_root` may not work for deployment.
    #        Double-check this! TD117
    #
    config_package_root = config.config.get('local_packages_path')

    version_path = os.path.join(
        config_package_root,
        package,
        version,
    )

    install_path = os.path.join(version_path, rezzurect_config.INSTALL_FOLDER_NAME)

    # TODO : Running makedirs here is not be necessary for every package.
    #        Consider removing.
    #
    if not os.path.isdir(install_path):
        os.makedirs(install_path)

    environment.init(source_path, install_path)
    manager.install(package, root, config_package_root, version=version)


def run_with_rez(package_name, version, runner, app_args):
    '''Execute a repository package's main command.

    Args:
        package_name (str):
            The name of the installed rez package. This is the "name"
            variable defined in `package_name`/`version`/package.py file.
        version (str):
            The specific install of the installed rez package. This is the "version"
            variable defined in `package_name`/`version`/package.py file.
        runner (`BaseAdapter`):
            The class used to actually run the command in the user's Rez package.
        app_args (str):
            Any arguments the application may require

    Raises:
        EnvironmentError: If the Rez installation could not be found.
        RuntimeError: If the package could not be built or installed.

    '''
    add_rez_to_sys_path_if_needed(runner)

    source_path = os.path.join(
        rezzurect_config.REZ_PACKAGE_ROOT_FOLDER,
        package_name,
        version,
    )

    if not os.path.isdir(source_path):
        raise RuntimeError('Path "{source_path}" could not be found.'.format(source_path=source_path))

    package_module = get_package_module(source_path, package_name)

    if not package_module:
        raise RuntimeError('source_path "{source_path}" has no package.py file.'.format(
            source_path=source_path))

    packages = ['{package_module.name}-{version}'.format(
        package_module=package_module, version=version)]

    context = get_context(packages)

    if not context:
        LOGGER.info('Package "%s" was not found. Attempting to build from scratch now.', packages)
        build_context_from_scratch(
            package_module.name,
            version,
            rezzurect_config.REZ_PACKAGE_ROOT_FOLDER,
            source_path,
        )
        context = get_context(packages)

    if not context:
        raise RuntimeError('The package(s) "{packages}" could not be found or built.'.format(packages=packages))

    return runner.execute(package_name, version, context, app_args)
