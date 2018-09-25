# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.


"""
Hook that loads defines all the available actions, broken down by publish type.
"""
import collections
import os
import re

import sgtk
from sgtk import TankError
from sgtk.platform.qt import QtGui

# First flame version with the Python API is 2018.2
if sgtk.platform.current_engine().is_version_less_than("2018.2"):
    flame = None
else:
    import flame

HookBaseClass = sgtk.get_hook_baseclass()

####################################################################################################
# Constants to be used with Flame

SETUP_ACTION = "load_setup"
CLIP_ACTION = "load_clip"
SHOT_LOAD_ACTION = "load_batch"
SHOT_CREATE_ACTION = "create_batch"


class FlameLoaderActionError(Exception):
    pass


class FlameLoaderActions(HookBaseClass):
    ################################################################################################
    # public interface - to be overridden by deriving classes
    def generate_actions(self, sg_publish_data, actions, ui_area):
        """
        Returns a list of action instances for a particular publish.
        This method is called each time a user clicks a publish somewhere in the UI.
        The data returned from this hook will be used to populate the actions menu for a publish.

        The mapping between Publish types and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the loader app
        has already established *which* actions are appropriate for this object.

        The hook should return at least one action for each item passed in via the
        actions parameter.

        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.

        Because you are operating on a particular publish, you may tailor the output
        (caption, tooltip etc) to contain custom information suitable for this publish.

        The ui_area parameter is a string and indicates where the publish is to be shown.
        - If it will be shown in the main browsing area, "main" is passed.
        - If it will be shown in the details area, "details" is passed.
        - If it will be shown in the history area, "history" is passed.

        Please note that it is perfectly possible to create more than one action "instance" for
        an action! You can for example do scene introspection - if the action passed in
        is "character_attachment" you may for example scan the scene, figure out all the nodes
        where this object can be attached and return a list of action instances:
        "attach to left hand", "attach to right hand" etc. In this case, when more than
        one object is returned for an action, use the params key to pass additional
        data into the run_action hook.

        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """

        app = self.parent
        app.log_debug("Generate actions called for UI element %s. "
                      "Actions: %s. Publish Data: %s" % (ui_area, actions, sg_publish_data))

        action_instances = []

        if not flame:
            app.log_warning("Unable to import the Flame Python API")
            return action_instances

        if SETUP_ACTION in actions and hasattr(flame.batch, "append_setup"):
            action_instances.append({
                "name": SETUP_ACTION,
                "params": None,
                "caption": "Load and Append Batch Setup",
                "description": "Load and append a batch setup file to the current Batch Group."
            })

        if CLIP_ACTION in actions and hasattr(flame.batch, "import_clip"):
            action_instances.append({
                "name": CLIP_ACTION,
                "params": None,
                "caption": "Import Clip",
                "description": "Import a clip to the current Batch Group."
            })

        if SHOT_CREATE_ACTION in actions and hasattr(flame.batch, "create_batch_group"):
            action_instances.append({
                "name": SHOT_CREATE_ACTION,
                "params": None,
                "caption": "Create Batch Group",
                "description": "Create a Batch setup inside a new Batch Group."
            })

        if SHOT_LOAD_ACTION in actions and hasattr(flame.batch, "load_setup"):
            batch_paths = self._get_batch_path_from_sg_publish_data(sg_publish_data)
            if batch_paths is not None:
                action_instances.append({
                    "name": SHOT_LOAD_ACTION,
                    "params": None,
                    "caption": "Load in new Batch Group",
                    "description": "Load a Batch setup file inside a new Batch Group."
                })

        return action_instances

    def execute_multiple_actions(self, actions):
        """
        Executes the specified action on a list of items.

        The default implementation dispatches each item from ``actions`` to
        the ``execute_action`` method.

        The ``actions`` is a list of dictionaries holding all the actions to execute.
        Each entry will have the following values:

            name: Name of the action to execute
            sg_publish_data: Publish information coming from Shotgun
            params: Parameters passed down from the generate_actions hook.

        .. note::
            This is the default entry point for the hook. It reuses the ``execute_action``
            method for backward compatibility with hooks written for the previous
            version of the loader.

        .. note::
            The hook will stop applying the actions on the selection if an error
            is raised midway through.

        :param list actions: Action dictionaries.
        """
        for single_action in actions:
            name = single_action["name"]
            sg_publish_data = single_action["sg_publish_data"]
            params = single_action["params"]
            self.execute_action(name, params, sg_publish_data)

    def execute_action(self, name, params, sg_publish_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :returns: No return value expected.
        """

        app = self.parent
        app.log_debug("Execute action called for action %s. "
                      "Parameters: %s. Publish Data: %s" % (name, params, sg_publish_data))

        try:
            if name == CLIP_ACTION:
                self._import_clip(sg_publish_data)

            elif name == SETUP_ACTION:
                self._import_batch_file(sg_publish_data)

            elif name == SHOT_CREATE_ACTION:
                self._add_batch_group_from_shot(sg_publish_data, True)

            elif name == SHOT_LOAD_ACTION:
                self._add_batch_group_from_shot(sg_publish_data, False)

            else:
                raise FlameLoaderActionError("Unknown action name: '{}'".format(name))
        except FlameLoaderActionError, error:
            # A FlameActionError reaching here means that something major have
            # stopped the current action
            QtGui.QMessageBox.critical(
                None,
                "Error",
                str(error),
            )
            app.log_error(error)

    ################################################################################################
    # methods called by the menu options in the loader

    def _import_batch_file(self, sg_publish_data):
        """
        Imports a Batch setup into Flame.

        This function import the Batch setup into the current Batch Group.

        :param dict sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """

        app = self.parent
        app.log_debug("Importing batch file using '%s'" % sg_publish_data)

        setup_path = self.get_publish_path(sg_publish_data)

        # Directly load the setup if exists
        if setup_path and os.path.exists(setup_path):
            if not flame.batch.append_setup(setup_path):
                raise FlameLoaderActionError("Unable to load a Batch Setup")

        else:
            raise FlameLoaderActionError("File not found on disk - '%s'" % setup_path)

    def _import_clip(self, sg_publish_data):
        """
        Imports a clip into Flame.

        This function import the clip into self.import_location (Default: Schematic Reel 1)
        in the current Batch Group.

        :param dict sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """

        app = self.parent
        app.log_debug("Importing clip using '%s'" % sg_publish_data)

        clip_path = self.get_publish_path(sg_publish_data)

        # Load directly if the clip exists
        if clip_path and self._exists(clip_path):
            # The clip path exists so we can import it into Flame!
            if not flame.batch.import_clip(clip_path, self.import_location):
                raise FlameLoaderActionError("Unable to import '%s'" % clip_path)

        # The clip name doesn't directly exists, but it might
        # contain a pattern that we need to resolve.
        elif clip_path and '%' in clip_path:
            new_path = self._handle_frame_range(clip_path)["path"]

            # The sequence exists on disk
            if self._exists(new_path):
                if not flame.batch.import_clip(new_path, self.import_location):
                    raise FlameLoaderActionError("Unable to import '%s'" % clip_path)

            # The sequence doesn't exist on disk
            else:
                raise FlameLoaderActionError("Sequence not found on disk - '%s'" % new_path)

        # Clip path doesn't exists and doesn't contain any pattern
        else:
            raise FlameLoaderActionError("File not found on disk - '%s'" % clip_path)

    def _add_batch_group_from_shot(self, sg_publish_data, build_new):
        """
        Add a batch group into Flame.

        If build_new is True, it loads last version of every clip present in the Shot, otherwise it
        create the batch group using the latest version of the batch file present in the Shot
        (Do nothing if no batch file is present).

        :param dict sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :param bool build_new: Hint about if we should build a new batch group from the clip or
                               use the latest batch file
        """

        app = self.parent
        app.log_debug("Adding a batch group using '%s'" % sg_publish_data)

        sg_info = self._get_batch_info_from_sg_publish_data(sg_publish_data)
        if sg_info is None:
            raise FlameLoaderActionError("Cannot load a Batch Group from Shotgun using this Shot")

        # Create a new batch_group using this Shot
        if build_new:
            self._create_batch_group(sg_info)

        # Load the more recent batch file present on this Shot
        else:
            # Try to get the batch file from the current Shot
            batch_path = self._get_batch_path_from_published_files(sg_info)
            app.log_debug("Found Batch setup path: %s" % batch_path)
            # We found a batch file so let's import it
            if batch_path and self._exists(batch_path):
                app.log_debug(
                    "Creating the '%s' batch group using '%s'" % (
                        sg_publish_data['code'], batch_path
                    ))
                flame.batch.create_batch_group(sg_publish_data["code"])
                if not flame.batch.load_setup(batch_path):
                    raise FlameLoaderActionError("Unable to load the Batch Setup")

            # No batch file found
            else:
                raise FlameLoaderActionError("No setup to load")

    ################################################################################################
    # interface to the action hook configuration

    @property
    def supported_clip_types(self):
        """
        Query the action_mappings entry to get every Published Type that's considered as a clip

        :return: List of Published Type
        :rtype: [str]
        """

        return ["Flame Render"]

    @property
    def supported_batch_types(self):
        """
        Query the action_mappings entry to get every Published Type that's considered as
        a Batch file

        :return: List of Published Type
        :rtype: [str]
        """

        return [entry[0] for entry in self.parent.get_setting("action_mappings", {}).items() if
                SETUP_ACTION in entry[1]]

    @property
    def import_location(self):
        """
        Schematic Reel where the loader should import the clips.

        :return: Location to import clip
        :rtype: str
        """

        return os.environ.get("SHOTGUN_FLAME_IMPORT_LOCATION", "Schematic Reel 1")

    @property
    def want_write_file_node(self):
        """
        Define if we want to link a Write File node to a new Batch group

        Flame 2018.3 or above is needed for this functionality

        :return: Hint about using a linking a Write File node
        :rtype: bool
        """

        return bool(os.environ.get("SHOTGUN_FLAME_WANT_WRITE_FILE_NODE", True))

    @property
    def use_template(self):
        """
        Define if we want to use templates to generate de Write File node attribute.

        :return: Hint about using the templates to generate the Write File node attribute.
        :rtype: bool
        """

        return bool(os.environ.get("SHOTGUN_FLAME_USE_TEMPLATE", True))

    @property
    def media_path_root(self):
        """
        This path helps to setup the write_file_node by specifying where to write the medias.

        :return: Media path root
        :type: str
        """
        return os.environ.get(
            "SHOTGUN_FLAME_MEDIA_PATH_ROOT",
            self.parent.engine.get_setting("media_path_root", "")
        )

    @property
    def media_path_pattern(self):
        """
        This pattern helps to setup the write_file_node by specifying where to write the medias.

        :return: Media path pattern
        :type: str
        """
        return os.environ.get("SHOTGUN_FLAME_MEDIA_PATH_PATTERN", "<shot name>_{segment_name}_v<version>.<frame>")

    @property
    def media_file_type(self):
        """
        Media type to use with the Write File node.

        :return: Media file type
        :rtype: str
        """

        return os.environ.get("SHOTGUN_FLAME_MEDIA_FILE_TYPE", "OpenEXR")

    @property
    def clip_path_pattern(self):
        """
        This pattern helps to setup the write_file_node by specifying where to write the clips.

        :return: Clip path pattern
        :type: str
        """
        return os.environ.get("SHOTGUN_FLAME_CLIP_PATH_PATTERN", "<shot name>")

    @property
    def setup_path_pattern(self):
        """
        This pattern helps to setup the write_file_node by specifying where to write the setups.

        :return: Setup path pattern
        :type: str
        """
        return os.environ.get("SHOTGUN_FLAME_SETUP_PATH_PATTERN", "<shot name>.v<version>")

    @property
    def media_path_template(self):
        """
        Template built from the "write_file_media_path_template" entry from the configuration dictionary.

        :return: Media pattern path template
        :rtype: TemplatePath
        """

        return self.parent.sgtk.templates.get("flame_shot_comp_exr")

    @property
    def clip_path_template(self):
        """
        Template built from the "write_file_clip_path_template" entry from the configuration dictionary.

        :return: Clip path template
        :rtype: TemplatePath
        """

        return self.parent.sgtk.templates.get("flame_shot_clip")

    @property
    def setup_path_template(self):
        """
        Template built from the "write_file_setup_path_template" entry from the configuration dictionary.

        :return: Setup path template
        :rtype: TemplatePath
        """

        return self.parent.sgtk.templates.get("flame_shot_batch")

    @property
    def version_padding(self):
        """
        Padding to use on the version attribute on the Write File node.

        :return: Write File version padding
        :rtype: int
        """

        return int(os.environ.get("SHOTGUN_FLAME_VERSION_PADDING", 3))

    @property
    def frame_padding(self):
        """
        Padding to use on the frame attribute on the Write File node.

        :return: Write File frame padding
        :rtype: int
        """

        return int(os.environ.get("SHOTGUN_FLAME_FRAME_PADDING", 4))

    ##############################################################################################################
    # helper methods which can be subclassed in custom hooks to fine tune the behavior of things

    def _create_batch_group(self, shot_info):
        """
        Create a new Batch group using the current Shot information

        :param dict shot_info: Metadata of the current Shot
        """
        app = self.parent

        app.log_debug("Creating the batch group using '%s'" % shot_info)

        # Get the clips from sg_published_files
        clips = self._get_clips_from_published_files(shot_info)

        app.log_debug("Found clips %s" % clips)

        if not clips:
            raise FlameLoaderActionError("No clip to load")

        # Get the frame information of the Batch group from the sg_versions
        start_frame, last_frame = self._extract_frame_range_from_version(shot_info)

        # Start to build the Batch Group attribute dictionary
        batch_group_info = {"name": shot_info["code"]}

        # Add frame information to the batch_group dictionary if available
        if None not in [start_frame, last_frame]:
            batch_group_info["start_frame"] = start_frame
            batch_group_info["duration"] = (int(last_frame) - int(start_frame)) + 1

        if not flame.batch.create_batch_group(**batch_group_info):
            raise FlameLoaderActionError("Unable to create a Batch Group")

        have_write_file = False

        # Import every clips!
        for clip in clips:
            if self._exists(clip["path"]):
                app.log_debug("Importing '%s'" % clip["path"])

                node = flame.batch.import_clip(clip["path"], self.import_location)
                if node:
                    if self.want_write_file_node and not have_write_file:
                        clip["Shot Name"] = shot_info["code"]
                        clip["Sequence Name"] = shot_info["sg_sequence"]["name"]

                        self._link_write_node(node, clip)

                        have_write_file = True
                else:
                    self.parent.log_warning("Unable to load '%s'" % clip["path"])
            else:
                self.parent.log_warning("File not found on disk - '%s'" % clip["path"])

        flame.batch.organize()

    def _build_write_file_attribute(self, clip):
        """
        Build a dictionary of Write File node attribute using the clip information and the current context.

        :returns: Dictionary of Write file node attribute.
        :rtype: dict

        """
        fields = {
            "Sequence": clip["Sequence Name"],
            "Shot": "<shot name>",
            "segment_name": clip["Sequence Name"],
            "version": "<version>",
            "SEQ": "<frame>",
            "flame.frame" : "<frame>"
        }

        file_format = {
            "als": "Alias",
            "cin": "Cineon",
            "dpx": "Dpx",
            "jpg": "Jpeg",
            "jpeg": "Jpeg",
            "iff": "Maya",
            "exr": "OpenEXR",
            "pict": "Pict",
            "picio": "Pixar",
            "sgi": "Sgi",
            "pic": "Softimage",
            "tga": "Targa",
            "tif": "Tiff",
            "tiff": "Tiff",
            "rla": "Wavefront"
        }

        # The order is important when setting the attributes
        write_file_info = collections.OrderedDict()

        # Enable create_clip_path and include_setup
        write_file_info["create_clip"] = True

        # Enable include_setup_path
        write_file_info["include_setup"] = True

        # Enable version_number
        write_file_info["version_mode"] = "Custom Version"

        # The write file node have to be one version higher than the current clip
        write_file_info["version_number"] = clip["info"]["version_number"] + 1

        write_file_info["shot_name"] = clip["Shot Name"]
        write_file_info["name"] = clip["Shot Name"]

        media_path_set, clip_path_set, setup_path_set = [False] * 3

        # Specify where to write our media
        if self.use_template and self.media_path_template:
            media_root, media_path, media_ext = self._build_path_from_template(self.media_path_template, fields)
            write_file_info["media_path"] = media_root
            write_file_info["media_path_pattern"] = media_path
            while media_ext[0] == ".":
                media_ext = media_ext[1:]
            write_file_info["file_type"] = file_format.get(media_ext)

            keys = self.media_path_template.keys
            write_file_info["version_padding"] = int(keys['version'].format_spec)
            padding = keys.get("flame.frame", keys.get('SEQ', None))
            write_file_info["frame_padding"] = int(padding.format_spec) if padding is not None else 8

            media_path_set = True

        if not media_path_set and self.media_path_pattern:
            write_file_info["media_path"] = self.media_path_root
            write_file_info["media_path_pattern"] = self.media_path_pattern.format(**fields)

        if "version_padding" not in write_file_info and self.version_padding:
            write_file_info["version_padding"] = self.version_padding

        if "frame_padding" not in write_file_info and self.frame_padding:
            write_file_info["frame_padding"] = self.frame_padding

        if "file_type" not in write_file_info and self.media_file_type:
            write_file_info["file_type"] = self.media_file_type

        # Create a .clip file
        if self.use_template and self.clip_path_template:
            _, clip_path, _ = self._build_path_from_template(self.clip_path_template, fields)
            write_file_info["create_clip_path"] = clip_path

            clip_path_set = True

        if not clip_path_set and self.clip_path_pattern:
            write_file_info["create_clip_path"] = self.clip_path_pattern.format(**fields)

        # Create a .batch file
        if self.use_template and self.setup_path_template:
            _, setup_path, _ = self._build_path_from_template(self.setup_path_template, fields)
            write_file_info["include_setup_path"] = setup_path

            setup_path_set = True

        if not setup_path_set and self.setup_path_pattern:
            write_file_info["include_setup_path"] = self.setup_path_pattern.format(**fields)

        return write_file_info

    def _link_write_node(self, node, clip):
        """
        Links a write file node to the provided clip.

        :param PyNode node: Flame node to attach a Write File node to
        :param dict clip: Clip information of the node
        """

        app = self.parent
        app.log_debug("Linking a Write File node to '%s'" % clip)

        # Build the Write File node attribute dict
        param = self._build_write_file_attribute(clip)

        # Create the write file node
        write_node = flame.batch.create_node("Write File")

        if not write_node:
            raise FlameLoaderActions("Unable to create Write File node")

        # Param is a OrderedDict so the attributes are set in the right order
        for attribute, value in param.items():
            if hasattr(write_node, attribute):
                app.log_debug("Write File %s = %s" % (attribute, value))
                setattr(write_node, attribute, value)
            else:
                self.parent.log_warning("Unknown attribute: %s" % attribute)

        # Connect the Write File node to the node
        flame.batch.connect_nodes(node, "Default", write_node, "Front")

    def _get_info_from_published_files(self, sg_published_files):
        """
        Gets a list of paths associated to a list of published files. Specific to Flame as some paths
        need to be custom formatted (ie frames), and others need to be ignored (for instance, Batch files)

        :param [dict] sg_published_files: A list of Shotgun data dictionary with all the standard publish fields.
        :returns: A list of published file information.
        :rtype: [dict]
        """
        app = self.parent

        app.log_debug("Getting path and frame range information from '%s'" % sg_published_files)
        # First loop populates the list of valid published files in the shot
        published_files = []

        for published_file in sg_published_files:
            # Gets paths to published files
            sg_filters = [["id", "is", published_file["id"]]]
            sg_fields = ["path", "published_file_type", "version", "version_number", "code", "updated_at", "name"]
            sg_type = "PublishedFile"

            file_info = self.parent.shotgun.find_one(sg_type, filters=sg_filters, fields=sg_fields)

            try:
                # Get the local path of the published file
                path = self.get_publish_path(file_info)
            except TankError as error:
                # Unable to get the path so log it and ignore this published file
                self.parent.log_warning(str(error))
                continue

            # Eliminates PublishedFiles with an invalid local path
            try:
                if path and self._exists(path):
                    published_files.append({"path": path, "info": file_info})
                elif "%" in path:
                    path_info = self._handle_frame_range(path)

                    published_files.append(
                        {
                            "path": path_info["path"],
                            "frame_range":
                                {
                                    "start_frame": int(path_info["start_frame"]),
                                    "end_frame": int(path_info["end_frame"])
                                },
                            "info": file_info
                        }
                    )
                else:
                    self.parent.log_warning("File not found on disk - '%s'" % path)
            except FlameLoaderActionError as error:
                # Path not found so log it and ignore this published file
                self.parent.log_warning(str(error))
                continue

        app.log_debug("PublishedFile info found: %s" % published_files)

        return published_files

    def _get_batch_path_from_published_files(self, sg_info):
        """
        Gets the Batch File from a published files dictionary

        :param dict sg_info: A list of Shotgun data dictionary containing the published files.
        :returns: The path to the batch file.
        :rtype: str
        """
        app = self.parent
        app.log_debug("Getting batch path from the published files information")
        published_files_paths = self._get_info_from_published_files(
            sg_info["sg_published_files"]
        )

        batchs = []

        for published_file in published_files_paths:
            # Gets paths to published files

            info = published_file["info"]

            # We only want to play with batch file type
            if info["published_file_type"]["name"] in self.supported_batch_types:
                batchs.append(published_file)

        # We want to get the one with the latest iteration
        return self._latest_version_filter(batchs)[0]["path"] if batchs else None


    def _get_batch_info_from_sg_publish_data(self, sg_publish_data):
        """
        Gets the publish Batch file dictionnary from shotgun data dictionnary

        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :returns: A list of Shotgun data dictionary containing the published batch files.
        """

        sg_filters = [["id", "is", sg_publish_data["id"]]]
        sg_fields = ["sg_published_files",  # List of linked PublishedFile
                     "code",  # Name of the Shot
                     "sg_versions",  # List of linked Version
                     "sg_sequence"  # Linked Sequence
                    ]
        sg_type = "Shot"

        sg_info = self.parent.shotgun.find_one(
            sg_type, filters=sg_filters, fields=sg_fields
        )

        # Checks that we have the necessary info to proceed.
        if not all(f in sg_info for f in sg_fields):
            return None
        return sg_info

    def _get_batch_path_from_sg_publish_data(self, sg_publish_data):
        """
        Gets the current shot batch filefrom shotgun data dictionnary

        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :returns: The path to the batch file for the curent shot.
        """
        sg_info = self._get_batch_info_from_sg_publish_data(sg_publish_data)
        batch_path = self._get_batch_path_from_published_files(sg_info)
        return batch_path if batch_path and self._exists(batch_path) else None

    def _get_clips_from_published_files(self, sg_info):
        """
        Gets the clip files information from a published files dictionary

        :param dict sg_info: A list of Shotgun data dictionary containing the published files.
        :returns: A list of supported published file data.
        :rtype: [dict]
        """

        app = self.parent
        app.log_debug("Getting clips from the published files information")

        published_files_paths = self._get_info_from_published_files(
            sg_info["sg_published_files"]
        )

        clips = []

        for published_file in published_files_paths:
            # Gets paths to published files

            info = published_file["info"]

            # We don't want to play with file types that we don't support
            if info["published_file_type"]["name"] in self.supported_clip_types:
                clips.append(published_file)

        return self._latest_version_filter(clips)

    def _extract_frame_range_from_version(self, sg_info):
        """
        Try to get the frame range from the latest version of the entity.

        :param dict sg_info: Entity metadata
        :return: Tuple containing first and last frame
        :rtype: ( int, int )
        """
        app = self.parent
        app.log_debug("Getting version from '%s'" % sg_info)
        first_frame = None
        last_frame = None

        if "sg_versions" in sg_info and len(sg_info["sg_versions"]) > 0:
            latest_update = None

            for version in sg_info["sg_versions"]:
                filters = [["id", "is", version["id"]]]
                fields = ["frame_range", "updated_at"]
                entity_type = "Version"

                version_data = self.parent.shotgun.find_one(
                    entity_type, filters=filters, fields=fields
                )

                # Checks that we have the necessary info to proceed.
                if not all(f in version_data for f in fields):
                    raise FlameLoaderActionError("Cannot extract frame range for \n {}".format(sg_info))

                # Only if the frame_range is defined
                if version_data["frame_range"] is not None:
                    try:
                        # The current sg_version is more recent that the one we use
                        if latest_update is None or latest_update < version_data["updated_at"]:
                            latest_update = version_data["updated_at"]
                            first_frame, last_frame = list(map(int, version_data["frame_range"].split("-")))
                    except (AttributeError, ValueError):
                        pass

        app.log_debug("Found first frame = %s and last frame = %s" % (first_frame, last_frame))
        return first_frame, last_frame

    @staticmethod
    def _latest_version_filter(published_files_info):
        """
        Filter that keep the newest version of the Published Files.

        :param dict published_files_info: List of PublishedFile metadata
        :return: List of the latest PublishedFile metadata
        :rtype: [dict]
        """

        latest_clips = {}

        for clip in published_files_info:
            other_clip = latest_clips.get(clip["info"]["name"])

            # There's no other version of the clip so let's add this one
            if other_clip is None:
                latest_clips[clip["info"]["name"]] = clip
            else:
                # The other clip have a greater version so let's keep it
                if other_clip["info"]["version_number"] > clip["info"]["version_number"]:
                    continue

                # The other clip have a smaller version so let's swap them
                elif other_clip["info"]["version_number"] < clip["info"]["version_number"]:
                    latest_clips[clip["info"]["name"]] = clip

                # They both have the same version so let's keep the newest one
                else:
                    if other_clip["info"]["updated_at"] < clip["info"]["updated_at"]:
                        latest_clips[clip["info"]["name"]] = clip

        return latest_clips.values()

    @staticmethod
    def _handle_frame_range(path):
        """
        Takes a path and inserts formatted frame range for later use in Flame,
        using old-style Python formatting normally reserved for ints.

        :param str path: The path containing the formatting character.
        :return: Dictionary containing the sequence path, the first_frame and the last_frame
        :rtype: dict
        """

        ranges = FlameLoaderActions._guess_frame_range(path)

        # Cuts off everything after the position of the formatting char.
        path_end = path[path.find('%'):]

        # Get the formatting alone
        formatting_str = path_end[:path_end.find('d') + 1]

        # Gets the formatted frames numbers
        start_frame = formatting_str % int(ranges[0])
        end_frame = formatting_str % int(ranges[1])

        if None in [start_frame, end_frame]:
            raise FlameLoaderActionError("File not found on disk - '%s'" % path)
        elif start_frame == end_frame:
            frame_range = start_frame
        else:
            # Generates back the frame range, now formatted
            frame_range = "[{}-{}]".format(
                start_frame, end_frame
            )

        return {"path": path.replace(formatting_str, frame_range), "start_frame": start_frame, "end_frame": end_frame}

    @staticmethod
    def _guess_frame_range(path):
        """
        Try to get the sequence's frame range from the path

        :param str path: Path of the sequence containing a frame pattern
        :return: Tuple containing the first and the last frame number of the sequence or tuple of None if failure
        :rtype: ( int, int ) or ( None, None )
        """
        folder, file_name = os.path.split(path)
        match = re.match(r"(.*)(%\d+d)(.+)", file_name)

        if not match:
            raise FlameLoaderActionError("Cannot detect frame pattern for '%s'" % path)

        frame_list = []

        # The frame numbers have to match a certain number of digits
        frame_len = int(match.group(2)[1:-1])

        # Lets retrieve all the files that's in the folder of the file to match
        try:
            files = [f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        except OSError:
            raise FlameLoaderActionError("Unable to guess the frame range for '%s'" % path)

        for f in files:
            # It doesn't match our pattern
            if not f.startswith(match.group(1)) or not f.endswith(match.group(3)):
                continue

            # Lets isolate the potential frame number from the file name
            frame = f[len(match.group(1)):-len(match.group(3))]

            # It's not a frame that match our pattern
            if len(frame) != frame_len and not frame.isdigit():
                continue

            # Let's add the frame number of the file that match our pattern
            frame_list.append(frame)

        frame_list.sort()

        if len(frame_list) >= 2:
            # We have at least 2 frame so let's return first and the last frame number
            return frame_list[0], frame_list[-1]
        elif len(frame_list) == 1:
            # We only have one frame that match so let's return the same frame as begin and end frame
            return frame_list[0], frame_list[0]
        else:
            # Let's return None because nothing match our pattern
            return None, None

    @staticmethod
    def _exists(media_path):
        """
        Checks if the path exists directly or as a sequence

        :param str media_path: Potential media path
        :return: Return if the media_path exists
        :rtype: bool
        """

        # Check if the path exists
        if os.path.exists(media_path):
            return True

        folder, file_name = os.path.split(media_path)

        # Try to check if the path is a sequence
        match = re.match(r"(.*)(\[\d+-\d+\])(.+)", file_name)

        if not match or not os.path.exists(folder):
            # The path is not a sequence
            return False

        # Get the first and last frame of the sequence
        first, last = match.group(2).replace("[", "").replace("]", "").split("-")

        # Get the frame value padding length
        frame_size = len(first)

        # Check if at least one frame in the sequence exists
        for frame in range(int(first), int(last)):
            # Apply frame padding
            frame = "0" * (frame_size - len(str(frame))) + str(frame)

            # Build frame file name
            file_name = match.group(1) + frame + match.group(3)

            # Check if frame exists
            if os.path.exists(os.path.join(folder, file_name)):
                return True

        return False

    @staticmethod
    def _build_path_from_template(template, fields):
        """
        Build a path from a template and from a clip information dictionary.

        :param TemplatePath template: Template to use to build the path
        :param dict fields: Dictionary containing Shotgun Template keys and theirs values
        :return: Tuple containing the project root, the media path and the extension
        :rtype: ( str, str, str )
        """

        # Build the path from the template
        path = template._apply_fields(fields, ignore_types=["version", "SEQ", "flame.frame", "Shot", "segment_name"]) \
                   .replace(template.root_path, "", 1)[1:]  # remove the root path from the path and the first "/"

        path, ext = os.path.splitext(path)
        return template.root_path, path, ext.lower()
