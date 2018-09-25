# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from tank import Hook


class HieroGetShot(Hook):
    """
    This class implements a hook that can determines which Shotgun entity
    should be associated with each task and track item being exported.
    """
    def execute(self, task, item, data, **kwargs):
        """
        Takes a hiero.core.TrackItem as input and returns a data dictionary for
        the shot to update the cut info for.

        :param task: The Hiero task being processed.
        :param item: The hiero.core.TrackItem being processed.
        :param dict data: A dictionary with cached parent data.

        :returns: A Shot entity.
        :rtype: dict
        """
        # get the parent entity for the Shot
        parent = self.get_shot_parent(item.parentSequence(), data)

        # shot parent field
        parent_field = "sg_sequence"

        # grab shot from Shotgun
        sg = self.parent.shotgun
        filter = [
            ["project", "is", self.parent.context.project],
            [parent_field, "is", parent],
            ["code", "is", item.name()],
        ]

        # default the return fields to None to use the python-api default
        fields = kwargs.get("fields", None)
        shots = sg.find("Shot", filter, fields=fields)
        if len(shots) > 1:
            # can not handle multiple shots with the same name
            raise StandardError("Multiple shots named '%s' found", item.name())
        if len(shots) == 0:
            # create shot in shotgun
            shot_data = {
                "code": item.name(),
                parent_field: parent,
                "project": self.parent.context.project,
            }
            shot = sg.create("Shot", shot_data, return_fields=fields)
            self.parent.log_info("Created Shot in Shotgun: %s" % shot_data)
        else:
            shot = shots[0]

        # update the thumbnail for the shot
        upload_thumbnail = kwargs.get("upload_thumbnail", True)
        if upload_thumbnail:
            self.parent.execute_hook(
                "hook_upload_thumbnail",
                entity=shot,
                source=item.source(),
                item=item,
                task=kwargs.get("task")
            )

        return shot

    def get_shot_parent(self, hiero_sequence, data, **kwargs):
        """
        Given a Hiero sequence and data cache, return the corresponding entity
        in Shotgun to serve as the parent for contained Shots.

        .. note:: The data dict is typically the app's `preprocess_data` which
            maintains the cache across invocations of this hook.

        :param hiero_sequence: A Hiero sequence object
        :param dict data: A dictionary with cached parent data.

        :returns: A Shotgun entity.
        :rtype: dict
        """
        # stick a lookup cache on the data object.
        if "parent_cache" not in data:
            data["parent_cache"] = {}

        if hiero_sequence.guid() in data["parent_cache"]:
            return data["parent_cache"][hiero_sequence.guid()]

        # parent not found in cache, grab it from Shotgun
        sg = self.parent.shotgun
        filter = [
            ["project", "is", self.parent.context.project],
            ["code", "is", hiero_sequence.name()],
        ]

        # the entity type of the parent.
        par_entity_type = "Sequence"

        parents = sg.find(par_entity_type, filter)
        if len(parents) > 1:
            # can not handle multiple parents with the same name
            raise StandardError(
                "Multiple %s entities named '%s' found" %
                (par_entity_type, hiero_sequence.name())
            )

        if len(parents) == 0:
            # create the parent in shotgun
            par_data = {
                "code": hiero_sequence.name(),
                "project": self.parent.context.project,
            }
            parent = sg.create(par_entity_type, par_data)
            self.parent.log_info(
                "Created %s in Shotgun: %s" % (par_entity_type, par_data))
        else:
            parent = parents[0]

        # update the thumbnail for the parent
        upload_thumbnail = kwargs.get("upload_thumbnail", True)
        if upload_thumbnail:
            self.parent.execute_hook(
                "hook_upload_thumbnail",
                entity=parent,
                source=hiero_sequence,
                item=None
            )

        # cache the results
        data["parent_cache"][hiero_sequence.guid()] = parent

        return parent
