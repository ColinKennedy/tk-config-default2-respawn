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
Hook that handles logic and automation around automatic Flame project setup 
"""
import sgtk
from sgtk import TankError
import os
import re

HookBaseClass = sgtk.get_hook_baseclass()

class ProjectStartupActions(HookBaseClass):
    """
    Toolkit hook to control the behavior of how new projects are created.
    
    As part of the toolkit Flame launch process, a new Flame project is automatically
    created if it doesn't already exist. Toolkit will then jump directly into that project
    as part of the launch process. 
    
    This hooks allows a project to customize the behaviour for new projects and jumping into 
    projects:
    
    - The user which should be used when launching Flame and starting the project
    - The naming of a new project
    - The project parameters used with new projects
    - The storage volume to store a new project on
    - The workspace to use when launching the project
    
    It is possible to introspect Shotgun inside this hook, making it straight
    forward to make this entire process driven from field values within Shotgun.
    
    - The engine instance can be fetched via self.parent
    - A Shotgun API handle is available via engine_obj.shotgun.
    - The project id can be retrieved via engine_obj.context.project["id"]
    """
    
    def use_project_settings_ui(self):
        """
        Control if a project settings UI should appear for new projects.
        
        :returns: True if UI should show, false if not
        """
        return True
        
    def get_server_hostname(self):
        """
        Return the hostname of the machine which hosts the main Flame server,
        including storage and wiretap server access point.
        
        :returns: server hostname
        """
        return "localhost"
    
    def get_project_name(self):
        """
        Return the project name that should be used for the current context.
        Please note that Flame doesn't allow all types of characters in Project names.
        
        The Flame engine will try to find this project in Flame and start it.
        If it doesn't exist, it will be automatically created.
        
        :returns: project name string 
        """
        engine = self.parent
        
        if engine.context.project is None:
            raise TankError("Context does not have a project!")
        
        project_name = engine.context.project["name"]
        
        # sanity check the project name, convert to alphanumeric.
        # Flame is restrictive with special characters, so adopt 
        # a conservative approach
        sanitized_project_name = re.sub(r'\W+', '_', project_name)

        return sanitized_project_name

    def get_volume(self, volumes):
        """
        When a new project is created, this allows to control
        which volume should be associated with the new project.
        
        The return value needs to be one of the strings passed in 
        via the volumes parameter.
        
        :param volumes: List of existing volumes (list of string)
        :returns: One of the volumes in the list (str)
        """
        return volumes[0]
    
    def get_workspace(self):
        """
        Return the name of the workspace to use when opening a project.
        The system will create it if it doesn't already exist.
        
        If None is return, Flame will create a default workspace according
        to its standard workspace creation logic.
        
        :returns: A Flame workspace Name or None for a default workspace
        """
        return None

    def get_user(self):
        """
        Return the name of the Flame user to be used when launching this project.
        
        :returns: A user name as a string
        """
        engine = self.parent

        # Grab information about the environment we are running in
        shotgun_user = sgtk.util.get_current_user(engine.sgtk)

        if shotgun_user is None:
            user_name = "Shotgun Unknown"
            engine.log_warning("Toolkit was not able to map your machine user name to a "
                               "user in Shotgun. Your Flame project will be associated with a "
                               "default 'unknown' user. In order to correctly connect your Flame "
                               "user with the current Shotgun user, check that the current operating system "
                               "user name matches the 'login' field of one of the users in Shotgun. "
                               "Alternatively, if would like a different naming convention, either "
                               "reconfigure the Flame project startup hook or the Toolkit Core user " 
                               "resolve hook.")
        else:
            user_name = shotgun_user["name"] 

        # Note! Flame users are not compatible across DCC versions so there is a manual
        # process involved when upgrading. A common convention here is to generate one 
        # user per DCC version, so this is what the Shotgun integration will default to as well.
        full_user_name = "%s (v%s)" % (user_name, self.parent.flame_version) 

        return full_user_name
        
    def get_project_settings(self):
        """
        Returns project settings for when creating new projects.
        
        The following parameters need to be supplied:
        
         - FrameWidth (e.g. "1280")
         - FrameHeight (e.g. "1080")
         - FrameDepth (16-bit fp, 12-bit, 12-bit u, 10-bit, 8-bit) 
         - FieldDominance (PROGRESSIVE, FIELD_1, FIELD_2)
         - VisualDepth (8bits, 16bits)
         - AspectRatio (4:3, 16:9, or floating point value as string, e.g. '1.23423')
         - FrameRate ("23.976 fps", "24 fps", "25 fps", "29.97 fps DF", "29.97 fps NDF", "30 fps", "50 fps",
                      "59.94 fps DF", "59.94 fps NDF", "60 fps")
         
         For proxy settings for flame versions before 2016 ext 1, 
         see http://images.autodesk.com/adsk/files/wiretap2011_sdk_guide.pdf
         
         - ProxyEnable ("true" or "false")
         - ProxyWidthHint
         - ProxyDepthMode
         - ProxyMinFrameSize
         - ProxyAbove8bits ("true" or "false")
         - ProxyQuality (e.g "draft", "medium" etc)
         
         For proxy settings for flame versions from 2016 ext 1 and above,
         the following parameters can be specified
         
         - ProxyMinFrameSize (e.g. "960")
         - ProxyWidthHint ("0.5", "0.25" or "0.125")
         - ProxyQuality (e.g "lanczos", "medium" etc)
         - ProxyRegenState ("true" or "false")

        :returns: dictionary of standard wiretap style project setup parameters.
        """
        settings = {}
        settings["FrameWidth"] = "1920"
        settings["FrameHeight"] = "1080"
        settings["FrameDepth"] = "10-bit"
        settings["AspectRatio"] = "1.7778"
        settings["FieldDominance"] = "PROGRESSIVE"
        settings["FrameRate"] = "24 fps"
        settings["VisualDepth"] = "16bits"

        if self.parent.is_version_less_than("2016.1"):
            # proxy settings used in 2016 and below        
            settings["ProxyEnable"] = "false"
            settings["ProxyDepthMode"] = "8-bit"
            settings["ProxyQuality"] = "medium"
            settings["ProxyWidthHint"] = "720"
            settings["ProxyMinFrameSize"] = "0"
            settings["ProxyAbove8bits"] = "false"
        
        else:
            # proxy settings used in 2016 ext 1 and above
            # NOTE! In older versions of flame, ProxyWidthHint
            # was a resolution in pixels. On 2016.1+, it's a ratio (0.5)
            # if you customize this hook, please make sure that 
            # the correct values are specified.
            settings["ProxyRegenState"] = "false"
            settings["ProxyWidthHint"] = "0.5"
            settings["ProxyMinFrameSize"] = "960"
            settings["ProxyQuality"] = "lanczos"
        
        
        return settings
