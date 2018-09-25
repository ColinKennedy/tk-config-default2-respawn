# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

from tank.platform.qt import QtCore

def safe_to_string(value):
    """
    Safely convert the value to a string - handles
    unicode and QtCore.QString if using PyQt
    
    :param value:    The value to convert to a string
    :returns str:    utf8 encoded string of the input value
    """
    if isinstance(value, str):
        # it's a string anyway so just return
        return value
    
    if isinstance(value, unicode):
        # convert to utf-8
        return value.encode("utf8")

    if hasattr(QtCore, "QString"):
        # running PyQt!
        if isinstance(value, QtCore.QString):
            # QtCore.QString inherits from str but supports
            # unicode, go figure!  Lets play safe and return
            # a utf-8 string
            return str(value.toUtf8())

    # For everything else, just return as string
    return str(value)