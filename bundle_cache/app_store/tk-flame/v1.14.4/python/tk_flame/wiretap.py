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
Wiretap connection with the local Flame to carry out common setup operations


Some notes on debugging wiretap options
---------------------------------------

The wiretap options interface is best discovered by introspection.

In order to for example find out what project options are available for
a version of flame, you can do the following:

> /usr/discreet/wiretap/tools/current/wiretap_print_tree -d 1 -n /projects/my_project -s XML

This will dump the wiretap XML stream that is associated with the project
node /projects/my_project.

For more wiretap utilities, check out /usr/discreet/wiretap/tools/current

"""

import sgtk
import xml.dom.minidom as minidom
from sgtk import TankError

# helper exception class to trap all the C style errors
# that are potentially coming from the wiretap API.
class WiretapError(TankError):
    pass

# note: this is one of those C style library wrappers
# where each method internally is prefixed with
# WireTap, hence the dropping of the namespace.
try:
  from adsk.libwiretapPythonClientAPI import *
except ImportError:
  # Older version of Flame distributed that in the
  #/opt/Autodesk/<app>_<version>/python directory which required the current
  # working directory to be that directory in order to work.
  #
  from libwiretapPythonClientAPI import *

from .project_create_dialog import ProjectCreateDialog
from .qt_task import start_qt_app_and_show_modal

class WiretapHandler(object):
    """
    Wiretap functionality
    """

    #########################################################################################################
    # public methods

    def __init__(self):
        """
        Construction
        """
        self._engine = sgtk.platform.current_bundle()

        self._engine.log_debug("Initializing wiretap...")
        WireTapClientInit()

        # Instantiate a server handle
        host_name = self._engine.execute_hook_method("project_startup_hook", "get_server_hostname")
        self._server = WireTapServerHandle("%s:IFFFS" % host_name)
        self._engine.log_debug("Connected to wiretap host '%s'..." % host_name)

    def close(self):
        """
        Closes the wiretap connection
        """
        # Make sure to always uninitialize WireTap services in case of
        # exception, otherwise wiretap server will refuse all the
        # following connections.
        self._server = None
        WireTapClientUninit()
        self._engine.log_debug("Uninitialized wiretap...")

    def prepare_and_load_project(self):
        """
        Load and prepare the project represented by the current context

        :returns: arguments to pass to the Flame launch command line
        """
        user_name = self._engine.execute_hook_method("project_startup_hook", "get_user")
        project_name = self._engine.execute_hook_method("project_startup_hook", "get_project_name")
        workspace_name = self._engine.execute_hook_method("project_startup_hook", "get_workspace")

        self._ensure_project_exists(project_name, user_name, workspace_name)
        self._ensure_user_exists(user_name)

        if workspace_name is None:
            # use Flame's default workspace
            self._engine.log_debug("Using the Flame default workspace")
            app_args = "--start-project='%s' --start-user='%s' --create-workspace" % (project_name, user_name)

        else:
            self._engine.log_debug("Using a custom workspace '%s'" % workspace_name)
            # an explicit workspace is used. Ensure it exists
            self._ensure_workspace_exists(project_name, workspace_name)
            # and pass it to the startup
            app_args = "--start-project='%s' --start-user='%s' --create-workspace --start-workspace='%s'" % (project_name,
                                                                                                             user_name,
                                                                                                             workspace_name)

        return app_args

    #########################################################################################################
    # internals

    def _ensure_user_exists(self, user_name):
        """
        Ensures the given user exists

        :param user_name: Name of the user to look for
        """

        if not self._child_node_exists("/users", user_name, "USER"):
            # Create the new user
            users = WireTapNodeHandle(self._server, "/users")

            user_node = WireTapNodeHandle()
            if not users.createNode(user_name, "USER", user_node):
                raise WiretapError("Unable to create user %s: %s" % (user_name, users.lastError()))

            self._engine.log_debug("User %s successfully created" % user_name)

    def _ensure_workspace_exists(self, project_name, workspace_name):
        """
        Ensures that the given workspace exists

        :param project_name: Project to look in
        :param workspace_name: Workspace name to look for
        """

        if not self._child_node_exists("/projects/%s" % project_name, workspace_name, "WORKSPACE"):
            project = WireTapNodeHandle(self._server, "/projects/%s" % project_name)

            workspace_node = WireTapNodeHandle()
            if not project.createNode(workspace_name, "WORKSPACE", workspace_node):
                raise WiretapError("Unable to create workspace %s in "
                                   "project %s: %s" % (workspace_name, project_name, project.lastError()) )

        self._engine.log_debug("Workspace %s successfully created" % workspace_name)

    def _ensure_project_exists(self, project_name, user_name, workspace_name):
        """
        Ensures that the given project exists

        :param project_name: Project name to look for
        :param user_name: User name to use when starting up
        :param workspace_name: Workspace to use when starting up - if none, then default ws will be used.
        """
        from sgtk.platform.qt import QtGui, QtCore

        if not self._child_node_exists("/projects", project_name, "PROJECT"):

            # we need to create a new project!

            # first decide which volume to create the project on.
            # get a list of volumes and pass it to a hook which will
            # return the volume to use
            volumes = self._get_volumes()

            if len(volumes) == 0:
                raise TankError("Cannot create new project! There are no volumes defined for this Flame!")

            # call out to the hook to determine which volume to use
            volume_name = self._engine.execute_hook_method("project_startup_hook", "get_volume", volumes=volumes)

            # sanity check :)
            if volume_name not in volumes:
                raise TankError("Volume '%s' specified in hook does not exist in "
                                "list of current volumes '%s'" % (volume_name, volumes))

            host_name = self._engine.execute_hook_method("project_startup_hook", "get_server_hostname")

            # get project settings from the toolkit hook
            project_settings = self._engine.execute_hook_method("project_startup_hook", "get_project_settings")

            # now check if we should pop up a ui where the user can tweak the default prefs
            if self._engine.execute_hook_method("project_startup_hook", "use_project_settings_ui"):
                # at this point we don't have a QT application running, because we are still
                # in the pre-DCC launch phase, so need to wrap our modal dialog call
                # in a helper method which also creates a QApplication.

                (group_name, groups) = self._get_groups()
                (return_code, widget) = start_qt_app_and_show_modal("Create Flame Project",
                                                                    self._engine,
                                                                    ProjectCreateDialog,
                                                                    project_name,
                                                                    user_name,
                                                                    workspace_name,
                                                                    volume_name,
                                                                    volumes,
                                                                    host_name,
                                                                    group_name,
                                                                    groups,
                                                                    project_settings
                                                                    )

                if return_code == QtGui.QDialog.Rejected:
                    # user pressed cancel
                    raise TankError("Flame project creation aborted. Will not launch Flame.")

                # read updated settings back from the UI and update our settings dict with these
                for (k, v) in widget.get_settings().iteritems():
                    project_settings[k] = v

                volume_name = widget.get_volume_name()
                group_name = widget.get_group_name()

            else:
                self._engine.log_debug("Project settings ui will be bypassed.")
            # create the project : Using the command line tool here instead of the python API because we need root privileges to set the group id.
            import subprocess, os
            project_create_cmd = [
                os.path.join(self._engine.wiretap_tools_root, "wiretap_create_node"),
                "-n",
                os.path.join("/volumes", volume_name),
                "-d",
                project_name ]

            if not self._engine.is_version_less_than("2018.1"):
                project_create_cmd.append("-g")
                project_create_cmd.append(group_name)

            subprocess.check_call(project_create_cmd)

            # create project settings

            self._engine.log_debug("A new project '%s' will be created." % project_name)
            self._engine.log_debug("The following settings will be used:")
            for (k,v) in project_settings.iteritems():
                self._engine.log_debug("%s: %s" % (k, v))

            # create xml structure

            # NOTE! It seems the attribute order in the xml data may be significant
            # when the data is read into flame. Moving proxy parameters round in the past
            # has resulted in regressions, so ensure the xml structure is the intact
            # when making modifications.

            xml  = "<Project>"

            xml += "<Description>%s</Description>"             % "Created by Shotgun Flame Integration %s" % self._engine.version

            xml += self._append_setting_to_xml(project_settings, "SetupDir")
            xml += self._append_setting_to_xml(project_settings, "FrameWidth")
            xml += self._append_setting_to_xml(project_settings, "FrameHeight")
            xml += self._append_setting_to_xml(project_settings, "FrameDepth")
            xml += self._append_setting_to_xml(project_settings, "AspectRatio")
            xml += self._append_setting_to_xml(project_settings, "FrameRate")
            xml += self._append_setting_to_xml(project_settings, "ProxyEnable", stops_working_in="2016.1")
            xml += self._append_setting_to_xml(project_settings, "FieldDominance")
            xml += self._append_setting_to_xml(project_settings, "VisualDepth", starts_working_in="2015.3", stops_working_in="2018.0")

            # proxy settings
            xml += self._append_setting_to_xml(project_settings, "ProxyWidthHint")
            xml += self._append_setting_to_xml(project_settings, "ProxyDepthMode", stops_working_in="2016.1")
            xml += self._append_setting_to_xml(project_settings, "ProxyMinFrameSize")
            xml += self._append_setting_to_xml(project_settings, "ProxyAbove8bits", stops_working_in="2016.1")
            xml += self._append_setting_to_xml(project_settings, "ProxyQuality")

            # new proxy parameters added in 2016.1
            xml += self._append_setting_to_xml(project_settings, "ProxyRegenState", starts_working_in="2016.1")

            xml += "</Project>"

            # force cast to string - values coming from qt are unicode...
            xml = str(xml)

            # parse and pretty print xml to validate and aid debug
            pretty_xml = minidom.parseString(xml).toprettyxml()
            self._engine.log_debug("The following xml will be emitted: %s" % pretty_xml)

            # Set the project meta data
            project_node = WireTapNodeHandle(self._server, "/projects/" + project_name)
            if not project_node.setMetaData("XML", xml):
                raise WiretapError("Error setting metadata for %s: %s" % (project_name, project_node.lastError()))

            self._engine.log_debug( "Project successfully created.")

    def _append_setting_to_xml(self, project_settings, setting, starts_working_in=None, stops_working_in=None):
        """
        Generates xml for a parameter. May return an empty string if the xml
        cannot or should not be generated.

        :param project_settings: Dictionary of parameters
        :param setting: Setting to generate xml for
        :param starts_working_in: Version of flame that supports this setting.
                                  This is a string, e.g. '2016.1'. Passing this
                                  parameter means earlier versions of flame will
                                  ignore the parameter and return an empty string.
        :param stops_working_in: Version of Flame where this parameter stopped
                                 being supported. The reciprocal of starts_working_in.

        :returns: Empty string or '<setting>value</setting>'
        """
        xml = ""
        if project_settings.get(setting):

            if starts_working_in and self._engine.is_version_less_than(starts_working_in):
                # our version of flame is too old
                self._engine.log_warning("Ignoring '%s' directive since this is "
                                         "not supported by this version of Flame" % setting)

            elif stops_working_in and not self._engine.is_version_less_than(stops_working_in):
                # our version of flame is too new
                self._engine.log_warning("Ignoring '%s' directive since this is "
                                         "no longer supported by this version of Flame" % setting)

            else:
                xml = "<%s>%s</%s>" % (setting, project_settings.get(setting), setting)
        return xml

    def _get_volumes(self):
        """
        Return a list of volumes available

        :returns: List of volume names
        """
        root = WireTapNodeHandle(self._server, "/volumes")
        num_children = WireTapInt(0)
        if not root.getNumChildren(num_children):
            raise WiretapError("Unable to obtain number of volumes: %s" % root.lastError())

        volumes = []

        # iterate over children, look for the given node
        child_obj = WireTapNodeHandle()
        for child_idx in range(num_children):

            # get the child
            if not root.getChild(child_idx, child_obj):
                raise WiretapError("Unable to get child: %s" % root.lastError())

            node_name = WireTapStr()

            if not child_obj.getDisplayName(node_name):
                raise WiretapError("Unable to get child name: %s" % child_obj.lastError())

            volumes.append(node_name.c_str())

        return volumes

    def _get_groups(self):
        """
        Return the list of group available for the current user and the current group.

        :returns: (default_group, groups)
        """

        import pwd, grp, os
        # fetch all group which the user is a part of
        user = pwd.getpwuid(os.geteuid()).pw_name                         # current user
        groups = [g.gr_name for g in grp.getgrall() if user in g.gr_mem]  # compare user name with group database
        gid = pwd.getpwnam(user).pw_gid                                   # make sure current group is added if database if incomplete
        default_group = grp.getgrgid(gid).gr_name
        if default_group not in groups:
          groups.append(default_group)

        return (default_group, groups)

    def _child_node_exists(self, parent_path, child_name, child_type):
        """
        Helper method. Check if a wiretap node exists.

        :param parent_path: Parent node to scan
        :param child_name: Name of child node to look for
        :param child_type: Type of child node to look for
        :returns: True if node exists, false otherwise.
        """
        # get the parent
        parent = WireTapNodeHandle(self._server, parent_path)

        # get number of children
        num_children = WireTapInt(0)
        if not parent.getNumChildren(num_children):
            raise WiretapError("Wiretap Error: Unable to obtain number of "
                               "children for node %s. Please check that your "
                               "wiretap service is running. "
                               "Error reported: %s" % (parent_path, parent.lastError()))

        # iterate over children, look for the given node
        child_obj = WireTapNodeHandle()
        for child_idx in range(num_children):

            # get the child
            if not parent.getChild(child_idx, child_obj):
                raise WiretapError("Unable to get child: %s" % parent.lastError())

            node_name = WireTapStr()
            node_type = WireTapStr()

            if not child_obj.getDisplayName(node_name):
                raise WiretapError("Unable to get child name: %s" % child_obj.lastError())
            if not child_obj.getNodeTypeStr(node_type):
                raise WiretapError("Unable to obtain child type: %s" % child_obj.lastError())

            if node_name.c_str() == child_name and node_type.c_str() == child_type:
                return True

        return False
