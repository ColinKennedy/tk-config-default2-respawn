# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.        
        
import sgtk
from sgtk import TankError

def get_publish_type_field():
    """
    Get the field name to use when querying the published file type name
    for a Shotgun published file entity.

    :returns:   The name of the field to use
    """
    engine = sgtk.platform.current_bundle()
    publish_entity_type = sgtk.util.get_published_file_entity_type(engine.sgtk)
    if publish_entity_type == "PublishedFile":
        return "published_file_type.PublishedFileType.code"
    else:
        return "tank_type.TankType.code"

def update_publish_records(sg_publishes, min_fields = None):
    """
    If needed, update Shotgun publish records with fields required for
    use by the engine helper methods
    
    :param sg_publishes:    The list of publishes to check and update
    :param min_fields:      The minimum fields that must exist in the 
                            publish record.  If None then all fields
                            must exist.
    """
    engine = sgtk.platform.current_bundle()
        
    # ensure that all sg_publishes contain the information we need:
    required_fields = set(["name", "version", "path", "project", "entity", "task", get_publish_type_field()])
    if min_fields:
        required_fields.update(min_fields)
    else:
        min_fields = required_fields
    required_fields = list(required_fields)
    
    # check all publishes and find any that are missing one or more
    # required fields:
    to_update = {}
    for sg_publish in sg_publishes:
        for field in min_fields:
            if field not in sg_publish:
                # add to the list that need updating:
                to_update[sg_publish["id"]] = sg_publish
                break
            
    if to_update:
        try:
            # query shotgun for the record of any publishes that need updating:
            filters = [["id", "in", to_update.keys()]]
            sg_res = engine.shotgun.find(sg_publishes[0]["type"], filters, required_fields)
            
            # update the publish records:
            for sg_item in sg_res:
                to_update[sg_item["id"]].update(sg_item)
        except Exception, e:
            raise TankError("Failed to retrieve publish details from Shotgun: %s" % e)
