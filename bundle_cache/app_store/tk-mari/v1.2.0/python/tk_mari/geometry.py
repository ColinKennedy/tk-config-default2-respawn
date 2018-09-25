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
Additional Shotgun functionality that deals with Mari geometry
"""

import sgtk
from sgtk import TankError

import os
import mari

from .metadata import MetadataManager
from .utils import update_publish_records, get_publish_type_field

class GeometryManager(object):
    """
    Provides various utility methods that deal with Mari geometry
    """
    def __init__(self):
        """
        Construction
        """
        self.__md_mgr = MetadataManager()
    
    def find_geometry_for_publish(self, sg_publish):
        """
        Find the geometry and version instances for the specified publish if it exists in 
        the current project
        
        :param sg_publish:  The Shotgun publish to find geo for.  This should be a Shotgun 
                            entity dictionary containing at least the entity "type" and "id".
        :returns:           Tuple containing the geo and version that match the publish 
                            if found.
        """
        engine = sgtk.platform.current_bundle()
        
        # ensure that sg_publish contains the information we need:
        publish_type_field = get_publish_type_field()
        update_publish_records([sg_publish], ["project", "entity", "task", "name", publish_type_field])
        publish_entity = sg_publish["entity"]
        publish_task = sg_publish["task"]
        
        # enumerate through all geometry in project that has Shotgun metadata:
        found_geo = None
        sg_publish_version_ids = None
        for geo, entity, task in [(g.get("geo"), g.get("entity"), g.get("task")) for g in self.list_geometry()]:
            if not geo:
                continue
            
            # we can rule out the entire geo if it doesn't match the entity and/or task:
            if publish_entity and entity:
                if entity["type"] != publish_entity["type"] or entity["id"] != publish_entity["id"]:
                    continue
            if publish_task and task:
                if task["id"] != publish_task["id"]:
                    continue
            
            # enumerate through all versions of this geo that have Shotgun metadata:
            matches_geo = False
            for version_item in self.list_geometry_versions(geo):
                geo_version = version_item.get("geo_version")
                if not geo_version:
                    continue
                
                geo_version_publish_id = version_item.get("publish_id")
                if geo_version_publish_id == None:
                    # can't do much without a publish id!
                    continue
                
                if geo_version_publish_id == sg_publish["id"]:
                    # perfect match!
                    return (geo, geo_version)
                elif not matches_geo:
                    # didn't find an exact match so lets see if this is
                    # is a different version of the publish
                    if sg_publish_version_ids == None:
                        # get a list of publish versions from Shotgun that match sg_publish:
                        filters = [["project", "is", sg_publish["project"]]]
                        if publish_entity:
                            filters.append(["entity", "is", publish_entity])
                        if publish_task:
                            filters.append(["task", "is", publish_task])
                        if sg_publish["name"]:
                            filters.append(["name", "is", sg_publish["name"]])
                        if sg_publish[publish_type_field]:
                            filters.append([publish_type_field, "is", sg_publish[publish_type_field]])
                        sg_res = []
                        try:
                            sg_res = engine.shotgun.find(sg_publish["type"], filters, [])
                        except Exception, e:
                            raise TankError("Failed to query publish versions for publish '%s': %s" 
                                            % (sg_publish["name"], e))
                        sg_publish_version_ids = set([res["id"] for res in sg_res])
                        
                    if geo_version_publish_id in sg_publish_version_ids:
                        # found a matching publish that just differs by version
                        matches_geo = True
                
            if matches_geo:
                # didn't find an exact match for the version but did find the geo
                # so return that instead:
                return (geo, None)
                
        # didn't find a match :(
        return (None, None)
    
    def list_geometry(self):
        """
        Find all Shotgun aware geometry in the scene.  Any non-Shotgun aware geometry is ignored!

        :returns:   A list of dictionaries containing the geo together with any Shotgun metadata
                    that was found on it
        """
        all_geo = []
        for geo in mari.geo.list():
            metadata = self.__md_mgr.get_geo_metadata(geo)
            if not metadata:
                continue

            metadata["geo"] = geo
            all_geo.append(metadata)
            
        return all_geo
    
    def list_geometry_versions(self, geo):
        """
        Find all Shotgun aware versions for the specified geometry.  Any non-Shotgun aware versions are 
        ignored!

        :param geo: The Mari GeoEntity to find all versions for
        :returns:   A list of dictionaries containing the geo_version together with any Shotgun metadata
                    that was found on it
        """
        all_geo_versions = []
        for geo_version in geo.versionList():
            metadata = self.__md_mgr.get_geo_version_metadata(geo_version)
            if not metadata:
                continue
            
            metadata["geo_version"] = geo_version
            all_geo_versions.append(metadata)
            
        return all_geo_versions
    
    def load_geometry(self, sg_publish, options, objects_to_load):
        """
        Wraps the Mari GeoManager.load() method and additionally tags newly loaded geometry with Shotgun 
        specific metadata.  See Mari API documentation for more information on GeoManager.load().
                                
        :param sg_publish:      The shotgun publish to load.  This should be a Shotgun entity
                                dictionary containing at least the entity "type" and "id".
        :param options:         [Mari arg] - Options to be passed to the file loader when loading the geometry
        :param objects_to_load: [Mari arg] - A list of objects to load from the file
        :returns:               A list of the loaded GeoEntity instances that were created
        """
        # ensure that sg_publish contains the information we need:
        update_publish_records([sg_publish])        
        
        # extract the file path for the publish
        publish_path = self.__get_publish_path(sg_publish)
        if not publish_path or not os.path.exists(publish_path):
            raise TankError("Publish '%s' couldn't be found on disk!" % publish_path)
        
        # load everything:
        new_geo = []
        try:
            # (AD) Note - passing options as a named parameter (e.g. options=options) seems to
            # stop any channels specified in the options list from being created so just pass
            # as indexed parameters instead!
            new_geo = mari.geo.load(publish_path,
                                    options, 
                                    objects_to_load)
        except Exception, e:
            raise TankError("Failed to load published geometry from '%s': %s" % (publish_path, e))       
        
        # and initialize all new geo:
        for geo in new_geo:
            self.initialise_new_geometry(geo, publish_path, sg_publish)
            
        return new_geo 
    
    def add_geometry_version(self, geo, sg_publish, options):
        """
        Wraps the Mari GeoEntity.addVersion() method and additionally tags newly loaded geometry versions 
        with Shotgun specific metadata. See Mari API documentation for more information on 
        GeoEntity.addVersion().

        :param geo:             The Mari GeoEntity to add a version to
        :param sg_publish:      The publish to load as a new version.  This should be a Shotgun entity
                                dictionary containing at least the entity "type" and "id".
        :param options:         [Mari arg] - Options to be passed to the file loader when loading the geometry.  The
                                options will default to the options that were used to load the current version if
                                not specified.
        :returns:               The new GeoEntityVersion instance
        """
        # ensure that sg_publish contains the information we need:
        update_publish_records([sg_publish], min_fields = ["id", "path", "version_number"])        
        
        # extract the file path for the publish
        publish_path = self.__get_publish_path(sg_publish)
        if not publish_path or not os.path.exists(publish_path):
            raise TankError("Publish '%s' couldn't be found on disk!" % publish_path)
    
        # determine the name of the new version:
        version = sg_publish.get("version_number")
        version_name = "v%03d" % (version or 0)
        if version_name in geo.versionNames():
            raise TankError("Unable to add version as '%s' already exists for '%s'!"
                            % (version_name, geo.name()))
            
        # add the version
        try: 
            geo.addVersion(publish_path,
                           version_name, 
                           options)
        except Exception, e:
            raise TankError("Failed to load published geometry version from '%s': %s" % (publish_path, e))           
    
        # Make sure the version was successfully added:
        if version_name not in geo.versionNames():
             raise TankError("Failed to add geometry version '%s' to '%s'!"
                             % (version_name, geo.name()))
             
        geo_version = geo.version(version_name)
        
        # initialise the version:
        self.initialise_new_geometry_version(geo_version, publish_path, sg_publish)
        
        return geo_version

    def initialise_new_geometry(self, geo, publish_path, sg_publish):
        """
        Initialise a new geometry.  This sets the name and updates the Shotgun metadata.

        :param geo:             The geometry to initialise
        :param publish_path:    The path of the publish this geometry was loaded from
        :param sg_publish:      The Shotgun publish record for this geometry.  This should be a Shotgun
                                entity dictionary containing at least the entity "type" and "id".
        """
        # determine the name to use:
        publish_name = sg_publish.get("name")
        scene_name = os.path.basename(publish_path).split(".")[0]
        geo_name = publish_name or scene_name
        
        # look at the current name and see if it's merged or an individual entity:
        current_name = geo.name()
        if not current_name.startswith(publish_name) and not current_name.startswith(scene_name):
            # geo name should include the existing name as it's not merged!
            geo_name = "%s_%s" % (geo_name, current_name)
            
        if geo_name != current_name:
            # make sure the name is unique:
            test_name = geo_name
            test_index = 1
            existing_names = mari.geo.names()
            while True:
                if test_name not in existing_names:
                    # have unique name!
                    break
                test_name = "%s_%d" % (geo_name, test_index)
                test_index += 1
            geo_name = test_name
                
            # set the geo name:
            if geo_name != current_name:
                geo.setName(geo_name)
        
        # set the geo metadata:
        sg_project = sg_publish.get("project")            
        sg_entity = sg_publish.get("entity")
        sg_task = sg_publish.get("task")
        self.__md_mgr.set_geo_metadata(geo, sg_project, sg_entity, sg_task)
        
        # there should be a single version for the geo:
        geo_versions = geo.versionList()
        if len(geo_versions) != 1:
            raise TankError("Invalid number of versions found for geometry "
                            "- expected 1 but found %d!" % len(geo_versions))
        
        # finally, initialize the geometry version:
        self.initialise_new_geometry_version(geo_versions[0], publish_path, sg_publish)

    def initialise_new_geometry_version(self, geo_version, publish_path, sg_publish):
        """
        Initialise a new geometry version.  This sets the name and updates the Shotgun metadata.

        :param geo_version:     The geometry version to initialise
        :param publish_path:    The path of the publish this geometry was loaded from
        :param sg_publish:      The Shotgun publish record for this geometry version.  This should be a 
                                Shotgun entity dictionary containing at least the entity "type" and "id".
        """
        sg_publish_id = sg_publish.get("id")
        sg_version = sg_publish.get("version_number")
        
        # set geo_version name if needed:
        geo_version_name = "v%03d" % (sg_version or 0)
        if geo_version.name() != geo_version_name:
            geo_version.setName(geo_version_name)
            
        # and store metadata:
        self.__md_mgr.set_geo_version_metadata(geo_version, publish_path, sg_publish_id, sg_version)  

    def __get_publish_path(self, sg_publish):
        """
        Get the publish path from a Shotgun publish record.
        # (TODO) - move this to use a centralized method in core
        
        :param sg_publish:   The publish to extract the path from.
        :returns:            The path if found or None
        """
        return sg_publish.get("path", {}).get("local_path")

