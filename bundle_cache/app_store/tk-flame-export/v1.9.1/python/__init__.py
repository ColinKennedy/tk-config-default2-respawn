# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

# some of the modules are running as backburner jobs on the render farm
# and some are used to show UI dialogs.
#
# When launching the app in backburner, we need to make sure that we 
# don't try to import QT since that won't always be available.
# 
# We can probe this by trying to import QT using toolkit's generic
# mechanism - which will return a None value in case the import fails.
# in this case, we simply omit any of the QT modules below


# system wide stuff - always import
from . import export_utils

# only needed for UIs - don't import if we don't have QT:
from sgtk.platform.qt import QtCore
if QtCore:
    from . import dialogs

