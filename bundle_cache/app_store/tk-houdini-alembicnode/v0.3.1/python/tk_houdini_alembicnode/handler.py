# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# built-ins
import base64
import os
import sys
import zlib

try:
   import cPickle as pickle
except:
   import pickle

# houdini
import hou

# toolkit
import sgtk


class TkAlembicNodeHandler(object):
    """Handle Tk Alembic node operations and callbacks."""


    ############################################################################
    # Class data

    HOU_ROP_ALEMBIC_TYPE = "alembic"
    """Houdini type for alembic rops."""

    HOU_SOP_ALEMBIC_TYPE = "rop_alembic"  
    """Houdini type for alembic sops."""
    # this is correct. the houdini internal rop_alembic is a sop.

    NODE_OUTPUT_PATH_PARM = "filename"
    """The name of the output path parameter on the node."""

    TK_ALEMBIC_NODE_TYPE = "sgtk_alembic"
    """The class of node as defined in Houdini for the Alembic nodes."""

    TK_OUTPUT_CONNECTIONS_KEY = "tk_output_connections"
    """The key in the user data that stores the save output connections."""

    TK_OUTPUT_CONNECTION_CODEC = "sgtk-01"
    """The encode/decode scheme currently being used."""

    TK_OUTPUT_CONNECTION_CODECS = {
        "sgtk-01": {
            'encode': lambda data: \
                base64.b64encode(zlib.compress(pickle.dumps(data))),
            'decode': lambda data_str: \
                pickle.loads(zlib.decompress(base64.b64decode(data_str))),
        },
    }
    """Encode/decode schemes. To support backward compatibility if changes."""
    # codec names should not include a ":"

    TK_OUTPUT_PROFILE_PARM = "output_profile"
    """The name of the parameter that stores the current output profile."""

    TK_OUTPUT_PROFILE_NAME_KEY = "tk_output_profile_name"
    """The key in the user data that stores the output profile name."""


    ############################################################################
    # Class methods

    @classmethod
    def convert_back_to_tk_alembic_nodes(cls, app):
        """Convert Alembic nodes back to Toolkit Alembic nodes.

        :param app: The calling Toolkit Application

        Note: only converts nodes that had previously been Toolkit Alembic
        nodes.

        """

        # get all rop/sop alembic nodes in the session
        alembic_nodes = []
        alembic_nodes.extend(hou.nodeType(hou.sopNodeTypeCategory(),
            cls.HOU_SOP_ALEMBIC_TYPE).instances())
        alembic_nodes.extend(hou.nodeType(hou.ropNodeTypeCategory(),
            cls.HOU_ROP_ALEMBIC_TYPE).instances())

        if not alembic_nodes:
            app.log_debug("No Alembic Nodes found for conversion.")
            return

        # the tk node type we'll be converting to
        tk_node_type = TkAlembicNodeHandler.TK_ALEMBIC_NODE_TYPE

        # iterate over all the alembic nodes and attempt to convert them
        for alembic_node in alembic_nodes:

            # get the user data dictionary stored on the node
            user_dict = alembic_node.userDataDict()

            # get the output_profile from the dictionary
            tk_output_profile_name = user_dict.get(
                cls.TK_OUTPUT_PROFILE_NAME_KEY)

            if not tk_output_profile_name:
                app.log_warning(
                    "Almbic node '%s' does not have an output profile name. "
                    "Can't convert to Tk Alembic node. Continuing." %
                    (alembic_node.name(),)
                )
                continue

            # create a new, Toolkit Alembic node:
            tk_alembic_node = alembic_node.parent().createNode(tk_node_type)

            # find the index of the stored name on the new tk alembic node
            # and set that item in the menu.
            try:
                output_profile_parm = tk_alembic_node.parm(
                    TkAlembicNodeHandler.TK_OUTPUT_PROFILE_PARM)
                output_profile_index = output_profile_parm.menuLabels().index(
                    tk_output_profile_name)
                output_profile_parm.set(output_profile_index)
            except ValueError:
                app.log_warning("No output profile found named: %s" % 
                    (tk_output_profile_name,))

            # copy over all parameter values except the output path 
            _copy_parm_values(alembic_node, tk_alembic_node,
                excludes=[cls.NODE_OUTPUT_PATH_PARM])

            # copy the inputs and move the outputs
            _copy_inputs(alembic_node, tk_alembic_node)

            # determine the built-in operator type
            if alembic_node.type().name() == cls.HOU_SOP_ALEMBIC_TYPE:
                _restore_outputs_from_user_data(alembic_node, tk_alembic_node)
            elif alembic_node.type().name() == cls.HOU_ROP_ALEMBIC_TYPE:
                _move_outputs(alembic_node, tk_alembic_node)

            # make the new node the same color. the profile will set a color, 
            # but do this just in case the user changed the color manually
            # prior to the conversion.
            tk_alembic_node.setColor(alembic_node.color())

            # remember the name and position of the original alembic node
            alembic_node_name = alembic_node.name()
            alembic_node_pos = alembic_node.position()

            # destroy the original alembic node
            alembic_node.destroy()

            # name and reposition the new, regular alembic node to match the
            # original
            tk_alembic_node.setName(alembic_node_name)
            tk_alembic_node.setPosition(alembic_node_pos)

            app.log_debug("Converted: Alembic node '%s' to TK Alembic node."
                % (alembic_node_name,))

    @classmethod
    def convert_to_regular_alembic_nodes(cls, app):
        """Convert Toolkit Alembic nodes to regular Alembic nodes.

        :param app: The calling Toolkit Application

        """

        tk_node_type = TkAlembicNodeHandler.TK_ALEMBIC_NODE_TYPE

        # determine the surface operator type for this class of node
        sop_types = hou.sopNodeTypeCategory().nodeTypes()
        sop_type = sop_types[tk_node_type]

        # determine the render operator type for this class of node
        rop_types = hou.ropNodeTypeCategory().nodeTypes()
        rop_type = rop_types[tk_node_type]

        # get all instances of tk alembic rop/sop nodes
        tk_alembic_nodes = []
        tk_alembic_nodes.extend(
            hou.nodeType(hou.sopNodeTypeCategory(), tk_node_type).instances())
        tk_alembic_nodes.extend(
            hou.nodeType(hou.ropNodeTypeCategory(), tk_node_type).instances())

        if not tk_alembic_nodes:
            app.log_debug("No Toolkit Alembic Nodes found for conversion.")
            return

        # iterate over all the tk alembic nodes and attempt to convert them
        for tk_alembic_node in tk_alembic_nodes:

            # determine the corresponding, built-in operator type
            if tk_alembic_node.type() == sop_type:
                alembic_operator = cls.HOU_SOP_ALEMBIC_TYPE
            elif tk_alembic_node.type() == rop_type:
                alembic_operator = cls.HOU_ROP_ALEMBIC_TYPE
            else:
                app.log_warning("Unknown type for node '%s': %s'" %
                    (tk_alembic_node.name(), tk_alembic_node.type()))
                continue

            # create a new, regular Alembic node
            alembic_node = tk_alembic_node.parent().createNode(alembic_operator)

            # copy the file parms value to the new node
            filename = _get_output_menu_label(
                tk_alembic_node.parm(cls.NODE_OUTPUT_PATH_PARM))
            alembic_node.parm(cls.NODE_OUTPUT_PATH_PARM).set(filename)

            # copy across knob values
            _copy_parm_values(tk_alembic_node, alembic_node,
                excludes=[cls.NODE_OUTPUT_PATH_PARM])

            # store the alembic output profile name in the user data so that we
            # can retrieve it later.
            output_profile_parm = tk_alembic_node.parm(
                cls.TK_OUTPUT_PROFILE_PARM)
            tk_output_profile_name = \
                output_profile_parm.menuLabels()[output_profile_parm.eval()]
            alembic_node.setUserData(cls.TK_OUTPUT_PROFILE_NAME_KEY, 
                tk_output_profile_name)

            # copy the inputs and move the outputs
            _copy_inputs(tk_alembic_node, alembic_node)
            if alembic_operator == cls.HOU_SOP_ALEMBIC_TYPE:
                _save_outputs_to_user_data(tk_alembic_node, alembic_node)
            elif alembic_operator == cls.HOU_ROP_ALEMBIC_TYPE:
                _move_outputs(tk_alembic_node, alembic_node)

            # make the new node the same color
            alembic_node.setColor(tk_alembic_node.color())

            # remember the name and position of the original tk alembic node
            tk_alembic_node_name = tk_alembic_node.name()
            tk_alembic_node_pos = tk_alembic_node.position()

            # destroy the original tk alembic node
            tk_alembic_node.destroy()

            # name and reposition the new, regular alembic node to match the
            # original
            alembic_node.setName(tk_alembic_node_name)
            alembic_node.setPosition(tk_alembic_node_pos)

            app.log_debug("Converted: Tk Alembic node '%s' to Alembic node."
                % (tk_alembic_node_name,))

    @classmethod
    def get_all_tk_alembic_nodes(cls):
        """
        Returns a list of all tk-houdini-alembicnode instances in the current
        session.
        """

        tk_node_type = TkAlembicNodeHandler.TK_ALEMBIC_NODE_TYPE

        # get all instances of tk alembic rop/sop nodes
        tk_alembic_nodes = []
        tk_alembic_nodes.extend(
            hou.nodeType(hou.sopNodeTypeCategory(),
                         tk_node_type).instances())
        tk_alembic_nodes.extend(
            hou.nodeType(hou.ropNodeTypeCategory(),
                         tk_node_type).instances())

        return tk_alembic_nodes

    @classmethod
    def get_output_path(cls, node):
        """
        Returns the evaluated output path for the supplied node.
        """

        output_parm = node.parm(cls.NODE_OUTPUT_PATH_PARM)
        path = output_parm.menuLabels()[output_parm.eval()]
        return path

    ############################################################################
    # Instance methods

    def __init__(self, app):
        """Initialize the handler.
        
        :params app: The application instance. 
        
        """

        # keep a reference to the app for easy access to templates, settings,
        # logging methods, tank, context, etc.
        self._app = app

        # get and cache the list of profiles defined in the settings
        self._output_profiles = {}
        for output_profile in self._app.get_setting("output_profiles", []):
            output_profile_name = output_profile["name"]

            if output_profile_name in self._output_profiles:
                self._app.log_warning(
                    "Found multiple output profiles named '%s' for the "
                    "Tk Alembic node! Only the first one will be available." %
                    (output_profile_name,)
                )
                continue

            self._output_profiles[output_profile_name] = output_profile
            self._app.log_debug("Caching alembic output profile: '%s'" % 
                (output_profile_name,))


    ############################################################################
    # methods and callbacks executed via the OTLs

    # copy the render path for the current node to the clipboard
    def copy_path_to_clipboard(self):

        render_path = self._get_render_path(hou.pwd())

        # use Qt to copy the path to the clipboard:
        from sgtk.platform.qt import QtGui
        QtGui.QApplication.clipboard().setText(render_path)

        self._app.log_debug(
            "Copied render path to clipboard: %s" % (render_path,))


    # create an Alembic node, set the path to the output path of current node
    def create_alembic_node(self):

        current_node = hou.pwd()
        output_path_parm = current_node.parm(self.NODE_OUTPUT_PATH_PARM)
        alembic_node_name = 'alembic_' + current_node.name()

        # create the alembic node and set the filename parm
        alembic_node = current_node.parent().createNode(
            self.HOU_SOP_ALEMBIC_TYPE)
        alembic_node.parm(self.NODE_OUTPUT_PATH_PARM).set(
            output_path_parm.menuLabels()[output_path_parm.eval()])
        alembic_node.setName(alembic_node_name, unique_name=True)

        # move it away from the origin
        alembic_node.moveToGoodPosition()


    # get labels for all tk-houdini-alembic node output profiles
    def get_output_profile_menu_labels(self):

        menu_labels = []
        for count, output_profile_name in enumerate(self._output_profiles):
            menu_labels.extend([count, output_profile_name])

        return menu_labels


    # returns a list of menu items for the current node
    def get_output_path_menu_items(self):

        menu = ["sgtk"]
        current_node = hou.pwd()

        # attempt to compute the output path and add it as an item in the menu
        try:
            menu.append(self._compute_output_path(current_node))
        except sgtk.TankError as e:
            error_msg = ("Unable to construct the output path menu items: " 
                         "%s - %s" % (current_node.name(), e))
            self._app.log_error(error_msg)
            menu.append("ERROR: %s" % (error_msg,))

        return menu


    # apply the selected profile in the session
    def set_profile(self, node=None):

        if not node:
            node = hou.pwd()

        output_profile = self._get_output_profile(node)

        self._app.log_debug("Applying tk alembic node profile: %s" % 
            (output_profile["name"],))

        # apply the supplied settings to the node
        settings = output_profile["settings"]
        if settings:
            self._app.log_debug('Populating format settings: %s' % 
                (settings,))
            node.setParms(settings)

        # set the node color
        color = output_profile["color"]
        if color:
            node.setColor(hou.Color(color))

        self.refresh_output_path(node)

    # refresh the output profile path
    def refresh_output_path(self, node):

        output_path_parm = node.parm(self.NODE_OUTPUT_PATH_PARM)
        output_path_parm.set(output_path_parm.eval())

    # open a file browser showing the render path of the current node
    def show_in_fs(self):

        # retrieve the calling node
        current_node = hou.pwd()
        if not current_node:
            return

        render_dir = None

        # first, try to just use the current cached path:
        render_path = self._get_render_path(current_node)

        if render_path:
            # the above method returns houdini style slashes, so ensure these
            # are pointing correctly
            render_path = render_path.replace("/", os.path.sep)

            dir_name = os.path.dirname(render_path)
            if os.path.exists(dir_name):
                render_dir = dir_name

        if not render_dir:
            # render directory doesn't exist so try using location
            # of rendered frames instead:
            rendered_files = self._get_rendered_files(current_node)

            if not rendered_files:
                msg = ("Unable to find rendered files for node '%s'." 
                       % (current_node,))
                self._app.log_error(msg)
                hou.ui.displayMessage(msg)
                return
            else:
                render_dir = os.path.dirname(rendered_files[0])

        # if we have a valid render path then show it:
        if render_dir:
            # TODO: move to utility method in core
            system = sys.platform

            # run the app
            if system == "linux2":
                cmd = "xdg-open \"%s\"" % render_dir
            elif system == "darwin":
                cmd = "open '%s'" % render_dir
            elif system == "win32":
                cmd = "cmd.exe /C start \"Folder\" \"%s\"" % render_dir
            else:
                msg = "Platform '%s' is not supported." % (system,)
                self._app.log_error(msg)
                hou.ui.displayMessage(msg)

            self._app.log_debug("Executing command:\n '%s'" % (cmd,))
            exit_code = os.system(cmd)
            if exit_code != 0:
                msg = "Failed to launch '%s'!" % (cmd,)
                hou.ui.displayMessage(msg)


    # called when the node is created.
    def setup_node(self, node):

        default_name = self._app.get_setting('default_node_name')
        node.setName(default_name, unique_name=True)

        # apply the default profile
        self.set_profile(node)

        try:
            self._app.log_metric("Create", log_version=True)
        except:
            # ingore any errors. ex: metrics logging not supported
            pass


    ############################################################################
    # Private methods

    # compute the output path based on the current work file and cache template
    def _compute_output_path(self, node):

        # get relevant fields from the current file path
        work_file_fields = self._get_hipfile_fields()

        if not work_file_fields:
            msg = "This Houdini file is not a Shotgun Toolkit work file!"
            raise sgtk.TankError(msg)

        output_profile = self._get_output_profile(node)

        # Get the cache templates from the app
        output_cache_template = self._app.get_template_by_name(
            output_profile["output_cache_template"])

        # create fields dict with all the metadata
        fields = {
            "name": work_file_fields.get("name", None),
            "node": node.name(),
            "renderpass": node.name(),
            "SEQ": "FORMAT: $F",
            "version": work_file_fields.get("version", None),
        }

        fields.update(self._app.context.as_template_fields(
            output_cache_template))

        path = output_cache_template.apply_fields(fields)
        path = path.replace(os.path.sep, "/")

        return path


    # get the current output profile
    def _get_output_profile(self, node=None):

        if not node:
            node = hou.pwd()

        output_profile_parm = node.parm(self.TK_OUTPUT_PROFILE_PARM)
        output_profile_name = \
            output_profile_parm.menuLabels()[output_profile_parm.eval()]
        output_profile = self._output_profiles[output_profile_name]

        return output_profile
            

    # extract fields from current Houdini file using the workfile template
    def _get_hipfile_fields(self):
        current_file_path = hou.hipFile.path()

        work_fields = {}
        work_file_template = self._app.get_template("work_file_template")
        if (work_file_template and 
            work_file_template.validate(current_file_path)):
            work_fields = work_file_template.get_fields(current_file_path)

        return work_fields


    # get the render path from current item in the output path parm menu
    def _get_render_path(self, node):
        output_parm = node.parm(self.NODE_OUTPUT_PATH_PARM)
        path = output_parm.menuLabels()[output_parm.eval()]
        return path


    # returns the files on disk associated with this node
    def _get_rendered_files(self, node):

        file_name = self._get_render_path(node)

        output_profile = self._get_output_profile(node)

        # get the output cache template for the current profile
        output_cache_template = self._app.get_template_by_name(
            output_profile["output_cache_template"])

        if not output_cache_template.validate(file_name):
            msg = ("Unable to validate files on disk for node %s."
                   "The path '%s' is not recognized by Shotgun."
                   % (node.name(), file_name))
            self._app.log_error(msg)
            return []
            
        fields = output_cache_template.get_fields(file_name)

        # get the actual file paths based on the template. Ignore any sequence
        # or eye fields
        return self._app.tank.paths_from_template(
            output_cache_template, fields, ["SEQ", "eye"])


################################################################################
# Utility methods

# Copy all the input connections from this node to the target node.
def _copy_inputs(source_node, target_node):

    input_connections = source_node.inputConnections()
    num_target_inputs = len(target_node.inputConnectors())

    if len(input_connections) > num_target_inputs:
        raise hou.InvalidInput(
            "Not enough inputs on target node. Cannot copy inputs from "
            "'%s' to '%s'" % (source_node, target_node)
        )
        
    for connection in input_connections:
        target_node.setInput(connection.inputIndex(),
            connection.inputNode())


# Copy parameter values of the source node to those of the target node if a
# parameter with the same name exists.
def _copy_parm_values(source_node, target_node, excludes=None):

    if not excludes:
        excludes = []

    # build a parameter list from the source node, ignoring the excludes
    source_parms = [
        parm for parm in source_node.parms() if parm.name() not in excludes]

    for source_parm in source_parms:

        source_parm_template = source_parm.parmTemplate()

        # skip folder parms
        if isinstance(source_parm_template, hou.FolderSetParmTemplate):
            continue

        target_parm = target_node.parm(source_parm.name())

        # if the parm on the target node doesn't exist, skip it
        if target_parm is None:
            continue

        # if we have keys/expressions we need to copy them all.
        if source_parm.keyframes():
            for key in source_parm.keyframes():
                target_parm.setKeyframe(key)
        else:
            # if the parameter is a string, copy the raw string.
            if isinstance(source_parm_template, hou.StringParmTemplate):
                target_parm.set(source_parm.unexpandedString())
            # copy the evaluated value
            else:
                try:
                    target_parm.set(source_parm.eval())
                except TypeError:
                    # The pre- and post-script type comboboxes changed sometime around
                    # 16.5.439 to being string type parms that take the name of the language
                    # (hscript or python) instead of an integer index of the combobox item
                    # that's selected. To support both, we try the old way (which is how our
                    # otl is setup to work), and if that fails we then fall back on mapping
                    # the integer index from our otl's parm over to the string language name
                    # that the alembic node is expecting.
                    if source_parm.name().startswith("lpre") or source_parm.name().startswith("lpost"):
                        value_map = ["hscript", "python"]
                        target_parm.set(value_map[source_parm.eval()])
                    else:
                        raise


# return the menu label for the supplied parameter
def _get_output_menu_label(parm):
    if parm.menuItems()[parm.eval()] == "sgtk":
        # evaluated sgtk path from item
        return parm.menuLabels()[parm.eval()] 
    else:
        # output path from menu label
        return parm.menuItems()[parm.eval()] 


# move all the output connections from the source node to the target node
def _move_outputs(source_node, target_node):

    for connection in source_node.outputConnections():
        output_node = connection.outputNode()
        output_node.setInput(connection.inputIndex(), target_node)


# saves output connections into user data of target node. Needed when target
# node doesn't have outputs.
def _save_outputs_to_user_data(source_node, target_node):

    output_connections = source_node.outputConnections()
    if not output_connections:
        return

    outputs = []
    for connection in output_connections:
        output_dict = {
            'node': connection.outputNode().path(),
            'input': connection.inputIndex(),
        }
        outputs.append(output_dict)

    # get the current encoder for the handler
    handler_cls = TkAlembicNodeHandler
    codecs = handler_cls.TK_OUTPUT_CONNECTION_CODECS
    encoder = codecs[handler_cls.TK_OUTPUT_CONNECTION_CODEC]['encode']

    # encode and prepend the current codec name
    data_str = handler_cls.TK_OUTPUT_CONNECTION_CODEC + ":" + encoder(outputs)

    # set the encoded data string on the input node
    target_node.setUserData(handler_cls.TK_OUTPUT_CONNECTIONS_KEY, data_str)


# restore output connections from this node to the target node.
def _restore_outputs_from_user_data(source_node, target_node):

    data_str = source_node.userData(
        TkAlembicNodeHandler.TK_OUTPUT_CONNECTIONS_KEY)

    if not data_str:
        return

    # parse the data str to determine the codec used
    sep_index = data_str.find(":")
    codec_name = data_str[:sep_index]
    data_str = data_str[sep_index + 1:]

    # get the matching decoder based on the codec name
    handler_cls = TkAlembicNodeHandler
    codecs = handler_cls.TK_OUTPUT_CONNECTION_CODECS
    decoder = codecs[codec_name]['decode']

    # decode the data str back into original python objects
    outputs = decoder(data_str)

    if not outputs:
        return

    for connection in outputs:
        output_node = hou.node(connection['node'])
        output_node.setInput(connection['input'], target_node)

