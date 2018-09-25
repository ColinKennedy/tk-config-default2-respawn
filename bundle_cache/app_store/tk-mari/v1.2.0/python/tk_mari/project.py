# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Additional Shotgun functionality that deals with Mari Projects 
"""

import sgtk
from sgtk import TankError

import os
import mari

from .metadata import MetadataManager
from .geometry import GeometryManager
from .utils import update_publish_records

class ProjectManager(object):
    """
    Provides various utility methods that deal with Mari Projects
    """
    def __init__(self):
        """
        Construction
        """
        self.geo_mgr = GeometryManager()
        self.md_mgr = MetadataManager()
    
    def create_project(self, name, sg_publishes, channels_to_create, channels_to_import, 
                       project_meta_options, objects_to_load):
        """
        Wraps the Mari ProjectManager.create() method and additionally tags newly created project and all 
        loaded geometry & versions with Shotgun specific metadata. See Mari API documentation for more 
        information on ProjectManager.create().
                                        
        :param name:                    [Mari arg] - The name to use for the new project
        :param sg_publishes:            A list of publishes to load into the new project.  At least one publish
                                        must be specified!
        :param channels_to_create:      [Mari arg] - A list of channels to create for geometry in the new project
        :param channels_to_import:      [Mari arg] - A list of channels to import for geometry in the new project
        :param project_meta_options:    [Mari arg] - A dictionary of project creation meta options - these are
                                        typically the mesh options used when loading the geometry
        :param objects_to_load:         [Mari arg] - A list of objects to load from the files
        :returns:                       The newly created Project instance
        """
        engine = sgtk.platform.current_bundle()
        
        # make sure that a project with this name doesn't already exist:
        if name in mari.projects.names():
            raise TankError("A project called '%s' already exists!" % name)
        
        # ensure at least one publish was specified:
        if not sg_publishes:
            raise TankError("Must specify at least one valid geometry publish to create a new project with!")
        
        # ensure that all sg_publishes contain the information we need:
        update_publish_records(sg_publishes)
        
        # extract the file path for the first publish:
        # (TODO) - move this to use a centralized method in core
        publish_path = sg_publishes[0].get("path", {}).get("local_path")
        if not publish_path or not os.path.exists(publish_path):
            raise TankError("Publish '%s' couldn't be found on disk!" % publish_path)
        
        # close existing project if it's open:
        if mari.projects.current():
            mari.projects.close()
            if mari.projects.current():
                # the user cancelled and the project wasn't closed
                return
        
        # create the project with the first geometry specified:
        try:
            engine.log_debug("Creating a new project called: %s" % name)
            mari.projects.create(name,
                                 publish_path,
                                 channels_to_create, 
                                 channels_to_import,
                                 project_meta_options, 
                                 objects_to_load)
        except Exception, e:
            raise TankError("Failed to create new project: %s" % e)        
        
        # make sure that the current project is the one we created:
        new_project = mari.projects.current()
        if not new_project or new_project.name() != name:
            raise TankError("Newly created project '%s' wasn't opened!" % name)
        
        # add metadata to the project so that we can track the context:
        self.md_mgr.set_project_metadata(new_project, engine.context)        
        
        # update the metadata, name and version on the geometry that was
        # loaded as part of the project creation:
        for geo in mari.geo.list():
            self.geo_mgr.initialise_new_geometry(geo, publish_path, sg_publishes[0])
        
        # finally, load in any additional geometry that was selected:
        for sg_publish in sg_publishes[1:]:
            self.geo_mgr.load_geometry(sg_publish, project_meta_options, objects_to_load)
            
        return new_project






