# -*- coding: utf-8 -*-

name = 'rez'

version = '2.22.1'

requires = ['python-2.6+<3']

variants = [['platform-linux', 'arch-x86_64', 'os-CentOS-7.5.1804']]

def commands():
    env.PYTHONPATH.append('{this.root}')

timestamp = 1539453589

format_version = 2
