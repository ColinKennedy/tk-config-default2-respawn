#!/usr/bin/env python
# -*- coding: utf-8 -*-

# IMPORT STANDARD LIBRARIES
import os


def _get_config_root_directory():
    '''str: Get the absolute path of this Shotgun Pipeline configuration.'''
    return os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def init_config():
    '''Get this Pipeline Configuration's Rez config file and add it.'''
    config_file = get_config_path()
    os.environ['REZ_CONFIG_FILE'] = config_file


def get_config_path():
    '''str: Get the absolute path to this Pipeline Configuration's Rez config file.'''
    return os.path.join(_get_config_root_directory(), 'rez_packages', '.rezconfig')
