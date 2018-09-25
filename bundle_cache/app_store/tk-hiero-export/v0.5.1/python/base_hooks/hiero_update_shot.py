# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class HieroUpdateShot(HookBaseClass):
    """
    This class defines methods that handle updating the Shot entity
    in Shotgun, as well as whether and how the filesystem structure
    is created for a Shot during export.
    """
    def create_filesystem_structure(self, entity_type, entity_id, preset_properties):
        """
        Handles creating the filesystem structure for the shot that
        was exported. The preset properties dictionary is provided to
        allow for the lookup of any custom properties that might have
        been defined in other hooks, like can be achieved when using
        the hiero_customize_export_ui hook.

        Example Implementation:

        .. code-block:: python

            # Check our custom property to know whether we should create the filesystem
            # structure or not.
            if preset_properties.get("custom_create_filesystem_property", True):
                self.parent.logger.debug(
                    "Creating file system structure for %s %s..." % (entity_type, entity_id)
                )
                self.parent.sgtk.create_filesystem_structure(entity_type, [entity_id])
            else:
                self.parent.logger.debug("Not creating the filesystem structure!")

        :param str entity_type: The entity type that was created or
            updated as part of the export. Most likely this will be
            "Shot".
        :param int entity_id: The id of the entity that was created
            or updated as part of the export.
        :param dict preset_properties: The export preset's properties
            dictionary.
        """
        raise NotImplementedError

    def update_shotgun_shot_entity(self, entity_type, entity_id, entity_data, preset_properties):
        """
        Handles updating the Shot entity in Shotgun with the new data produced
        during the export. The preset properties dictionary is provided to
        allow for the lookup of any custom properties that might have been
        defined in other hooks, like can be achieved when using the
        hiero_customize_export_ui hook.

        Example Implementation:

        .. code-block:: python

            # If the custom bool property is False, we don't update the
            # sg_cut_in field on the Shot entity.
            if not preset_properties.get("custom_update_cut_in_property", True):
                del entity_data["sg_cut_in"]

            self.parent.sgtk.shotgun.update(entity_type, entity_id, entity_data)

        :param str entity_type: The entity type to update.
        :param int entity_id: The id of the entity to update.
        :param dict entity_data: The new data to update the entity with.
        :param dict preset_properties: The export preset's properties
            dictionary.
        """
        raise NotImplementedError
