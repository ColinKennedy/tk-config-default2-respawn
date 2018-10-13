#!/usr/bin/env python
# -*- coding: utf-8 -*-

# IMPORT STANDARD LIBRARIES
import tempfile
import sys
import os

# IMPORT THIRD-PARTY LIBRARIES
# This sys.path.append adds `rezzurect` and any other third-party library that we need
_CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
_SHOTGUN_CONFIG_ROOT = os.path.dirname(_CURRENT_DIR)
sys.path.append(os.path.join(_SHOTGUN_CONFIG_ROOT, 'vendors'))
sys.path.append(os.path.join(_SHOTGUN_CONFIG_ROOT, 'vendors', 'rez-2.22.1-py2.7.egg'))
import yaml


_CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))


def _get_config_root_directory():
    '''str: Get the absolute path of this Shotgun Pipeline configuration.'''
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def init_config():
    '''Get this Pipeline Configuration's Rez config file and add it.'''
    data = resolve_config_data(get_config_path())

    with tempfile.NamedTemporaryFile(delete=False) as file_:
        yaml.dump(data, file_)

    os.environ['REZ_CONFIG_FILE'] = file_.name


def get_config_path():
    '''str: Get the absolute path to this Pipeline Configuration's Rez config file.'''
    return os.path.join(_get_config_root_directory(), 'rez_packages', '.rezconfig')


def resolve_config_data(path):
    '''Use a base config file to create a "Pipeline-Configuration-aware" config.

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
