#!/usr/bin/env python
# -*- coding: utf-8 -*-

# IMPORT STANDARD LIBRARIES
import tempfile
import os

# IMPORT THIRD-PARTY LIBRARIES
# TODO : Remove this sys.path.append later
import sys
sys.path.append('/usr/lib64/python2.7/site-packages')
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
