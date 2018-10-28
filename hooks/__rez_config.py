#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''A module that helps bootstrap Rez onto Shotgun's Pipeline Configuration.'''

# IMPORT STANDARD LIBRARIES
import tempfile
import sys
import os

# IMPORT THIRD-PARTY LIBRARIES
_CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
_SHOTGUN_CONFIG_ROOT = os.path.dirname(_CURRENT_DIR)
_VENDORS_PATH = os.path.join(_SHOTGUN_CONFIG_ROOT, 'vendors')
# This sys.path.append adds `rezzurect` and any other third-party library that we need
sys.path.append(_VENDORS_PATH)
sys.path.append(os.path.join(_VENDORS_PATH, 'rez-2.23.1-py2.7'))

from rezzurect.utils import rezzurect_config
import yaml


rezzurect_config.init_custom_pythonpath()


def _get_config_root_directory():
    '''str: Get the absolute path of this Shotgun Pipeline configuration.'''
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


# TODO : Make it so that, if REZ_CONFIG_FILE is not defined, we define it
#        but use it if it IS defined
#
def init_config():
    '''Get this Pipeline Configuration's Rez config file and add it.

    Important:
        This is the linchpin that keeps Shotgun and Rez working together.
        Make changes to this function only if you know what you're doing.

    '''
    data = resolve_config_data(get_config_path())

    with tempfile.NamedTemporaryFile(delete=False) as file_:
        yaml.dump(data, file_)

    os.environ['REZ_CONFIG_FILE'] = file_.name


def get_config_path():
    '''str: Get the absolute path to this Pipeline Configuration's Rez config file.'''
    return os.path.join(_get_config_root_directory(), '.rezconfig')


def resolve_config_data(path):
    '''Use a base config file to create a "Pipeline-Configuration-aware" config.

    Note:
        Rez requires that the path to the .rezconfig file and all of the paths
        listed in the .rezconfig file to be hardcoded. Normally that's fine but
        Shotgun complicates this requirement because, depending on how you source
        the Pipeline Configuration, it may actually be copied and installed to
        the user folder.

        Since there's no way to know beforehand which Shotgun sourcing method
        is being used, we use a fake ".rezconfig" file as a template, fill in its
        paths as absolute paths, and then source it instead.

    Args:
        path (str):
            The absolute path to a rez config file.
            The config file will presumably have one or more keys with
            "{root}" in its value which need to be "resolved" into absolute paths.

    Returns:
        dict[str]: The resolved configuration settings.

    '''
    with open(path, 'r') as file_:
        data = yaml.load(file_)

    path = data['package_definition_python_path']
    raw_path = path.format(root=_CURRENT_DIR)
    normalized = os.path.normpath(raw_path)
    data['package_definition_python_path'] = normalized

    return data
