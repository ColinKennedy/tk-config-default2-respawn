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
from sgtk.util import get_current_user


class FrameworkDemos(sgtk.platform.Application):
    """
    Demo and QA Toolkit app building blocks.
    """

    def init_app(self):
        """
        Initialize the app.
        """

        self.__demo_entities = {}

        payload = self.import_module("tk_multi_demo")

        # define a callback method to show the dialog
        def callback():
            payload.dialog.show_dialog(self)

        self.engine.register_command(
            "Shotgun Toolkit Demos",
            callback,
            {"short_name": "demos"}
        )

    def get_demo_entity(self, entity_type=None):
        """
        Return an entity of supplied type that is a good candidate for demo'ing.

        If the entity type is None, the currently authenticated HumanUser will
        be returned.
        """

        if not entity_type:
            entity_type = "HumanUser"

        if entity_type not in self.__demo_entities:

            entity = None

            # TODO: add other types here
            if entity_type == "Project":
                if self.context.project:
                    entity = self.context.project
                else:
                    entity = self.shotgun.find_one(entity_type, [])
            elif entity_type == "HumanUser":
                entity = get_current_user(self.sgtk)
            else:
                 # TODO: can we filter this at all?
                 entity = self.shotgun.find_one(entity_type, [])

            if not entity:
                return None

            self.__demo_entities[entity_type] = entity

        return self.__demo_entities[entity_type]

