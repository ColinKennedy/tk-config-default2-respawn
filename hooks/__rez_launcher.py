#!/usr/bin/env python
# -*- coding: utf-8 -*-

# IMPORT STANDARD LIBRARIES
import imp
import sys
import os

# IMPORT THIRD-PARTY LIBRARIES
# This sys.path.append adds `rezzurect`
_CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
_SHOTGUN_CONFIG_ROOT = os.path.dirname(_CURRENT_DIR)
sys.path.append(os.path.join(_SHOTGUN_CONFIG_ROOT, 'vendors'))

from rezzurect import environment

_REZ_PACKAGE_ROOT = os.path.join(_SHOTGUN_CONFIG_ROOT, 'rez_packages')


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


def get_context(packages):
    from rez import resolved_context
    from rez import exceptions

    try:
        return resolved_context.ResolvedContext(packages)
    except exceptions.PackageFamilyNotFoundError:
        return


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


def build_context_from_scratch(package, version, root, source_path):
    # '''Build the `package` recursively.

    # Note:
    #     This function assumes that `package` has not been built before.
    #     "Partial" building is not supported and old files will be overwritten.

    # Args:
    #     package (str): The name of the Rez package to build.
    #     version (str): The specific release of `package` to build.
    #     source_path (str): The absolute path to where the package/version files exist.

    # '''
    from rezzurect import manager
    from rez import config

    config_package_root = config.config.get('local_packages_path')
    build_path = os.path.join(source_path, 'build')

    version_path = os.path.join(
        config_package_root,
        package.name,
        version,
    )

    install_path = os.path.join(version_path, package.install_root)

    if not os.path.isdir(install_path):
        os.makedirs(install_path)

    # TODO : `environment.init` is needless. It should just be part of the adapter or not at all
    environment.init(package.name, version, source_path, build_path, install_path)
    manager.install(package.name, root, config_package_root, version=version)


def run_with_rez(package_name, version, runner, app_args):
    '''Execute a repository packages main command.

    Args:
        package_name (str):
            The name of the installed rez package. This is the "name"
            variable defined in `package_name`/{version}/package.py file.
        version (str):
            The specific install of the installed rez package. This is the "version"
            variable defined in `package_name`/{version}/package.py file.
        runner (`BaseAdapter`):
            The class used to actually run the command in the user's Rez package.
        app_args (str):
            Any arguments the application may require

    Raises:
        EnvironmentError: If the Rez installation could not be found.
        RuntimeError: If the package could not be built or installed.

    '''
    add_rez_to_sys_path_if_needed(runner)

    source_path = os.path.join(_REZ_PACKAGE_ROOT, package_name, version)
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
        build_context_from_scratch(package_module, version, _REZ_PACKAGE_ROOT, source_path)
        context = get_context(packages)

    if not context:
        raise RuntimeError('The package(s) "{packages}" could not be found or built.'.format(packages=packages))

    return runner.execute(package_name, version, context, app_args)
