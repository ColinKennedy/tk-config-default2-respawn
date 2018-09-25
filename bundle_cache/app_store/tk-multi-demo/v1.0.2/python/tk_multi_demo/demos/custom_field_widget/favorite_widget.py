# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

# import the shotgun_fields module from the qtwidgets framework
shotgun_fields = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_fields")

# the default shotgun fields checkbox widget
DefaultCheckBoxWidget = shotgun_fields.checkbox_widget.CheckBoxWidget


class MyProjectFavoritesWidget(DefaultCheckBoxWidget):
    """
    A custom display widget for the Project entity's "favorite" field.

    Shotgun also displays this field in a custom way.
    """

    # defining the meta class will register this class for use by the
    # field manager widget factory. the simple act of importing this class
    # will be enough to register it and apply it to the project favorite field.
    __metaclass__ = shotgun_fields.ShotgunFieldMeta

    # make this class usable as both an editor and display widget for fields
    # of type "checkbox"
    _DISPLAY_TYPE = "checkbox"
    _EDITOR_TYPE = "checkbox"

    # define which specific entities & fields this widget should be used for
    _ENTITY_FIELDS = [("Project", "current_user_favorite")]

    # NOTE: Here we are subclassing the default shotgun fields check box
    # widget and applying a different style to it (see the demo's style.qss
    # file).
