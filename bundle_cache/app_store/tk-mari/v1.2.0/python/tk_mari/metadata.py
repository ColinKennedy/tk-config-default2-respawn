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
Manage Shotgun metadata on Mari geometry, geometry versions and projects
"""

"""
# When testing, this should print out a continuous list of data without
# any blanks!

print "---------------"
print "Project:"
print mari.projects.current().metadata("tk_project_id")
print mari.projects.current().metadata("tk_entity_type")
print mari.projects.current().metadata("tk_entity_id")
print mari.projects.current().metadata("tk_step_id")
print mari.projects.current().metadata("tk_task_id")
print "---------------"
print "Geo:"
for geo in mari.geo.list():
    print "   %s" % geo.name()
    print "   - %s" % geo.metadata("tk_project_id")
    print "   - %s" % geo.metadata("tk_project")
    print "   - %s" % geo.metadata("tk_entity_type")
    print "   - %s" % geo.metadata("tk_entity_id")
    print "   - %s" % geo.metadata("tk_entity")
    print "   - %s" % geo.metadata("tk_task_id")
    print "   - %s" % geo.metadata("tk_task")

    print "   ---------------"
    print "   Versions:"
    for geo_version in geo.versionList():
        print "     %s" % geo_version.name()
        print "     - %s" % geo_version.metadata("tk_path")
        print "     - %s" % geo_version.metadata("tk_publish_id")
        print "     - %s" % geo_version.metadata("tk_version")
"""    

import mari

class MetadataManager(object):
    """
    Provides methods for setting and getting metadata on various Mari
    entities
    """
    
    # Shotgun metadata definition for a Mari Project entity
    __PROJECT_METADATA_INFO = {
        "project_id":{"display_name":"Shotgun Project Id", "visible":False},
        "entity_type":{"display_name":"Shotgun Entity Type", "visible":False, "default_value":""},
        "entity_id":{"display_name":"Shotgun Entity Id", "visible":False},
        "step_id":{"display_name":"Shotgun Step Id", "visible":False},
        "task_id":{"display_name":"Shotgun Task Id", "visible":False}
    }
    
    # Shotgun metadata definition for a Mari GeoEntity entity
    __GEO_METADATA_INFO = {
        "project_id":{"display_name":"Shotgun Project Id", "visible":False},
        "project":{"display_name":"Shotgun Project", "visible":True, "default_value":""},
        "entity_type":{"display_name":"Shotgun Entity Type", "visible":False, "default_value":""},
        "entity_id":{"display_name":"Shotgun Entity Id", "visible":False},
        "entity":{"display_name":"Shotgun Entity", "visible":True, "default_value":""},
        "task_id":{"display_name":"Shotgun Task Id", "visible":False},
        "task":{"display_name":"Shotgun Task", "visible":True, "default_value":""}
    }
    
    # Shotgun metadata definition for a Mari GeoEntityVersion entity
    __GEO_VERSION_METADATA_INFO = {
        "path":{"display_name":"Shotgun Project Id", "visible":True, "default_value":""},
        "publish_id":{"display_name":"Shotgun Project", "visible":True},
        "version":{"display_name":"Shotgun Entity Type", "visible":True}
    }

    def __init__(self):
        """
        Construction
        """
        pass
    
    def get_metadata(self, mari_entity):
        """
        General method that can be used to retrieve all Shotgun metadata from
        Mari GeoEntity, GeoEntityVersion and Project objects.
        
        Note, GeoVersionEntity and Project types aren't currently provided on
        the mari module so we have to use the PythonQt.private.* types instead.
        
        :param mari_entity: The mari entity to query metadata from.
        :returns:           Dictionary containing all Shotgun metadata found
                            in the Mari entity.
        """
        # If we're given nothing, then we don't have any metadata
        # to return. This is most likely the case due to an empty
        # session of Mari running. Once a project file has been
        # opened this is unlikely to happen.
        if mari_entity is None:
            return {}

        if mari.app.version().major() >= 3:
            geoEntityType = mari.GeoEntity 
            projectEntityType = mari.Project
        else:
            # Mari pre-3.0 release. If we fail on the import or
            # when referencing the geo and project entity classes
            # then we're likely in an empty Mari session with no
            # active project, in which case we have no metadata
            # and can return an empty dict.
            geoEntityType = None
            projectEntityType = None
            import PythonQt
            try:
                geoEntityType = PythonQt.private.GeoEntityVersion
            except AttributeError:
                pass

            try:
                projectEntityType = PythonQt.private.Project
            except AttributeError:
                pass

        if isinstance(mari_entity, mari.GeoEntity):
            return self.get_geo_metadata(mari_entity)
        elif geoEntityType and isinstance(mari_entity, geoEntityType):
            return self.get_geo_version_metadata(mari_entity)
        elif projectEntityType and isinstance(mari_entity, projectEntityType):
            return self.get_project_metadata(mari_entity)
        else:
            # metadata on other entity types isn't supported!
            return {}
    
    def set_project_metadata(self, mari_project, ctx):
        """
        Set the Toolkit metadata on a project

        :param mari_project:    The mari project entity to set the metadata on
        :param ctx:             The context to use when setting the metadata
        """
        metadata = {}
        metadata["project_id"] = ctx.project["id"]
        if ctx.entity:
            metadata["entity_type"] = ctx.entity["type"]
            metadata["entity_id"] = ctx.entity["id"]
        if ctx.step:
            metadata["step_id"] = ctx.step["id"]
        if ctx.task:
            metadata["task_id"] = ctx.task["id"]
            
        self.__set_metadata(mari_project, metadata, MetadataManager.__PROJECT_METADATA_INFO)
    
    def get_project_metadata(self, mari_project):
        """
        Get the toolkit metadata for a project
        
        :param mari_project:    The mari project entity to retrieve the metadata from
        :returns:               A dictionary of all metadata found on the project
        """
        return self.__get_metadata(mari_project, MetadataManager.__PROJECT_METADATA_INFO)
    
    def set_geo_metadata(self, geo, project, entity, task):
        """
        Set the Toolkit metadata on a GeoEntity
                        
        :param geo:     The mari GeoEntity to set the metadata on
        :param project: The Shotgun project to use when setting the metadata
        :param entity:  The Shotgun entity to use when setting the metadata
        :param task:    The Shotgun task to use when setting the metadata
        """
        metadata_info = MetadataManager.__GEO_METADATA_INFO.copy()
        
        # define the metadata we want to store:
        metadata = {}
        if project:
            metadata["project_id"] = project["id"]
            metadata["project"] = project.get("name")
        if entity:
            metadata_info["entity"]["display_name"] = "Shotgun %s" % entity.get("type") or "Entity"
            metadata["entity_type"] = entity["type"]
            metadata["entity_id"] = entity["id"]
            metadata["entity"] = entity.get("name")
        if task:
            metadata["task_id"] = task["id"]
            metadata["task"] = task["name"] 
        
        self.__set_metadata(geo, metadata, metadata_info)
    
    def get_geo_metadata(self, geo):
        """
        Get the toolkit metadata for a GeoEntity
        
        :param geo:     The mari GeoEntity to retrieve the metadata from
        :returns:       A dictionary of all metadata found on the GeoEntity        
        """
        raw_md = self.__get_metadata(geo, MetadataManager.__GEO_METADATA_INFO)
        
        # process the metadata back into Shotgun entities:
        md = {}
        if "project_id" in raw_md:
            project = {"type":"Project", "id":raw_md["project_id"]}
            if "project" in raw_md:
                project["name"] = raw_md["project"]
            md["project"] = project
            
        if "entity_type" in raw_md and "entity_id" in raw_md:
            entity = {"type":raw_md["entity_type"], "id":raw_md["entity_id"]}
            if "entity" in raw_md:
                entity["name"] = raw_md["entity"]
            md["entity"] = entity

        if "task_id" in raw_md:
            task = {"type":"Task", "id":raw_md["task_id"]}
            if "task" in raw_md:
                task["name"] = raw_md["task"]
            md["task"] = task
        
        return md    
    
    def set_geo_version_metadata(self, geo_version, path, publish_id, version):
        """
        Set the Toolkit metadata on a GeoEntityVersion

        :param geo_version: The mari GeoEntityVersion to set the metadata on
        :param path:        The publish path to use when setting the metadata
        :param publish_id:  The publish id to use when setting the metadata
        :param version:     The publish version number to use when setting the metadata
        """
        # define the metadata we want to store:
        metadata = {"path":path, "publish_id":publish_id,"version":version}
        
        self.__set_metadata(geo_version, metadata, MetadataManager.__GEO_VERSION_METADATA_INFO)
    
    def get_geo_version_metadata(self, geo_version):
        """
        Get the toolkit metadata for a GeoEntityVersion

        :param geo_version: The mari GeoEntityVersion to retrieve the metadata from
        :returns:           A dictionary of all metadata found on the GeoEntityVersion       
        """
        return self.__get_metadata(geo_version, MetadataManager.__GEO_VERSION_METADATA_INFO)
    
    def __set_metadata(self, obj, metadata, md_details):
        """
        Set the specified metadata on the specified object
                            
        :param obj:         The Mari object to add the metadata to
        :param metadata:    The metadata to add
        :param md_details:  Definitions of the metadata to add.
        """
        for name, details in md_details.iteritems():
            value = metadata.get(name, details.get("default_value"))
            if value == None:
                continue
    
            md_name = "tk_%s" % name
            
            obj.setMetadata(md_name, value)
            if "display_name" in details:
                obj.setMetadataDisplayName(md_name, details["display_name"])
                
            flags = obj.METADATA_SAVED
            visible = details.get("visible", True)
            if visible:
                flags |= obj.METADATA_VISIBLE
            obj.setMetadataFlags(md_name, flags)
    
    def __get_metadata(self, obj, md_details):
        """
        Get the specified metadata from the specified object
        
        :param obj:         The Mari object to get the metadata from
        :param md_details:  Definitions of the metadata to retrieve        

        :returns:           A dictionary containing the metadata retrieved from the object
        """
        metadata = {}
        for name, _ in md_details.iteritems():
            md_name = "tk_%s" % name
            if obj.hasMetadata(md_name):
                metadata[name] = obj.metadata(md_name)
        return metadata
    
