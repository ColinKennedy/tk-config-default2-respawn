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


class HieroUpdateCuts(HookBaseClass):
    """
    This class defines methods that control if and how Cuts and CutItems
    are created or updated during the export process.
    """
    def allow_cut_updates(self, preset_properties):
        """
        Determines whether to process the associated Cut entity during
        export. The preset properties provided allow for customization
        of this behavior based on custom properties added to the shot
        processor preset via other hooks, such as the
        customize_export_ui hook.

        :param dict preset_properties: The properties dictionary of
            shot processor preset.

        :returns: True to allow Cut updates, False to disallow.
        :rtype: bool
        """
        return True

    def create_cut_item(self, cut_item_data, preset_properties):
        """
        Handles the creation of the CutItem entity in Shotgun. This
        hook method can be overridden in order to put conditions on
        whether or how this creation occurs. The preset's properties
        are provided to allow for looking up custom properties that
        might have been added to the preset in other hooks, like can
        be achieved when using the hiero_customize_export_ui hook.

        :param dict cut_item_data: The dictionary of field/value
            pairs to use when creating the CutItem entity in Shotgun.
        :param dict preset_properties: The export preset's properties
            dictionary.

        :returns: The created CutItem entity dictionary, or None if
            no CutItem entity was created.
        :rtype: dict or None
        """
        cut_item = self.parent.sgtk.shotgun.create("CutItem", cut_item_data)
        self.parent.logger.info("Created CutItem in Shotgun: %s" % cut_item)
        return cut_item

    def get_cut_thumbnail(self, cut, task_item, preset_properties):
        """
        Gets the path to a thumbnail image to use when updating the
        export's associated Cut's thumbnail image. If None is returned
        by this method, the Cut's thumbnail will not be updated.

        :param dict cut: The Cut entity dictionary associated with the
            export.
        :param task_item: The TrackItem object associated with the export
            task.
        :param dict preset_properties: The export preset's properties
            dictionary.

        :returns: The path to the thumbnail image, or None if no thumbnail
            is to be uploaded to Shotgun.
        :rtype: str or None
        """
        thumbnail = None

        # Some additional documentation from The Foundry might help here:
        #
        # https://learn.foundry.com/hiero/developers/1.8/hieropythondevguide/api/api_core.html#hiero.core.TrackItem.sequence
        # https://learn.foundry.com/hiero/developers/1.8/hieropythondevguide/api/api_core.html#hiero.core.Sequence
        hiero_sequence = task_item.sequence()

        try:
            # See if we can find a poster frame for the sequence and
            # turn that into a usable thumbnail.
            thumbnail = hiero_sequence.thumbnail(hiero_sequence.posterFrame())
        except Exception:
            self.parent.logger.debug(
                "Unable to generate a thumbnail from the sequence's posterFrame."
            )

        return thumbnail