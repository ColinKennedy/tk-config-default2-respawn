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
Hook used by the create Mari project app to get the arguments that should be used
when creating a new project.
"""

import sgtk
from sgtk import TankError

import mari

HookBaseClass = sgtk.get_hook_baseclass()

class GetArgsHook(HookBaseClass):
    
    def get_project_creation_args(self, sg_publish_data):
        """
        Get the arguments to use when creating a new project from a selection
        of Published geometry files.
        
        Further details about these arguments can be found in the Mari api
        documentation (Help->SDK->Python->Documentation from the Mari menu)
        
        :param sg_publish_data: A list of the Shotgun publish records that will
                                be loaded to initialize the new project.
        :returns:               A dictionary of creation args that should contain
                                any of the following entries:
                                                        
                                'channels_to_create'
                                - Details of any channels that should be created
                                  in the new project.
                                
                                'channels_to_import'
                                - Details of any channels to be imported into the
                                  new project
                                  
                                'project_meta_options'
                                - Options to use when importing geometry from the
                                  published files
                                  
                                'objects_to_load'
                                - Specific objects to be loaded from the published
                                  files.
        """
        creation_args = {}
        
        # lets use default channels:
        creation_args["channels_to_create"] = []
        creation_args["channels_to_import"] = []

        # define the options to be used for the geometry import:
        #
        project_meta_options = {}
        # prefer uvV (UDIM) over ptex
        project_meta_options["MappingScheme"] = mari.projects.UV_OR_PTEX
        # create selection sets from face groups based on shader assignments
        project_meta_options["CreateSelectionSets"] = mari.geo.SELECTION_GROUPS_CREATE_FROM_FACE_GROUPS
        # merge nodes within file but not all geometry into a single mesh
        project_meta_options["MergeType"] = mari.geo.MERGETYPE_JUST_MERGE_NODES
                
        creation_args["project_meta_options"] = project_meta_options
        
        # specific objects to load from within geometry files - default (None) 
        # will load everything
        creation_args["objects_to_load"] = None
        
        return creation_args