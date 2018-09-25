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
import pprint
import cgi
import sys
import os
        
class ExportPreset(object):
    """
    Wrapper class that handles the Flame export preset.
    """
    
    def __init__(self, raw_preset):
        """
        Constructor
        
        :param raw_preset: The raw info.yml dictionary for this preset.
        """
        self._app = sgtk.platform.current_bundle()
        self._raw_preset = raw_preset
    
    def __repr__(self):
        return "<ExportPreset %r>" % self._raw_preset 
    
    def __get_publish_name(self, template, path):
        """
        Creates a name suitable for a Shotgun publish given a path.
        Will return a default name in case name extraction cannot be done.
        
        :param template: Template object to use for field extraction
        :param path: Path to generate name for
        :returns: Publish name as a string
        """
        # put together a name for the publish. This should be on a form without a version
        # number, so that it can be used to group together publishes of the same kind.        
        if template is None or not template.validate(path):
            self._app.log_warning("%s Cannot generate a publish name for '%s'!" % (template, path))
            publish_name = "Unknown"
        
        else:
            fields = template.get_fields(path)
            publish_name = "%s, %s" % (fields.get("Shot"), fields.get("segment_name"))
        
        return publish_name

    def get_name(self):
        """
        :returns: The name of this export preset
        """
        return self._raw_preset["name"]

    ############################################################################################################
    # values relating to the render output
    
    def get_render_template(self):
        """
        :returns: The render template object for this preset
        """
        render_template_name = self._raw_preset["template"]
        return self._app.get_template_by_name(render_template_name)        
    
    def get_batch_render_template(self):
        """
        Returns the batch render template object for this preset.
        
        Compatibility notes:
        
        Flame changed its logic for how this work in 2016.1 so we have to maintain
        two sets of logic for this method - one to handle 2016.1+ and one for
        previous versions. In 2016.1, it is possible to have separate paths for
        plate and batch renders. Before then, there were only plate paths.        
        
        :returns: Template object representing the batch render location
        """
        
        if self._app.engine.is_version_less_than("2016.1"):
            # pre-2016.1 - everything is a plate render template.
            return self.get_render_template()
        
        else:
            # 2016.1+ - flame supports both a plate location and a 
            # a batch location. 
            #
            # If the batch render template is none, fall back on the 
            # std plate render template

            batch_render_template_name = self._raw_preset["batch_render_template"]
            
            if batch_render_template_name:
                return self._app.get_template_by_name(batch_render_template_name)
            else:
                self._app.log_debug("batch_render_template not defined for %s - " 
                                    "falling back on std render template" % self)
                return self.get_render_template()
    
    def get_render_publish_type(self):
        """
        :returns: The publish type to use for renders
        """
        return self._raw_preset["publish_type"]

    def get_render_publish_name(self, path):
        """
        Generate a name suitable for a publish based on the render template

        :param path: Path to generate name for
        :returns: A name suitable for a render publish
        """
        return self.__get_publish_name(self.get_render_template(), path)

    def get_batch_render_publish_name(self, path):
        """
        Generate a name suitable for a publish based on the batch render template

        :param path: Path to generate name for
        :returns: A name suitable for a render publish
        """
        return self.__get_publish_name(self.get_batch_render_template(), path)


    def get_handles_length(self):
        """
        Returns the length of the requested frame handles that should be generated
        for each clip.

        :return: Handle length in frames
        """
        return self._raw_preset["frame_handles"]

    def get_cut_type(self):
        """
        Returns the name for cuts created by this preset

        :return: cut name as string
        """
        return self._raw_preset["cut_type"]

    ############################################################################################################
    # values relating to the quicktime output

    def highres_quicktime_enabled(self):
        """
        :returns: True if a high res quicktime should be generated, False if not.
        """
        return self.get_quicktime_template() is not None
    
    def batch_highres_quicktime_enabled(self):
        """
        :returns: True if a high res batch quicktime should be generated, False if not.
        """
        return self.get_batch_quicktime_template() is not None
    
    def get_quicktime_template(self):
        """
        :returns: The template for quicktimes on disk, None if no quicktimes should be written
        """
        quicktime_template_name = self._raw_preset["quicktime_template"]
        if quicktime_template_name:
            return self._app.get_template_by_name(quicktime_template_name)
        else:
            return None
        
    def get_batch_quicktime_template(self):
        """
        :returns: The template for batch render quicktimes on disk, 
                  None if no quicktimes should be written
        """
        batch_quicktime_template_name = self._raw_preset["batch_quicktime_template"]
        if batch_quicktime_template_name:
            return self._app.get_template_by_name(batch_quicktime_template_name)
        else:
            return None

    def batch_quicktime_path_from_render_path(self, batch_render_path):
        """
        Given a batch render path, generate a quicktime path.
        This method is analogous to quicktime_path_from_render_path()
        below.
        
        :path batch_render_path: A batch render path associated with this preset
        :returns: Path to a batch quicktime, resolved via the quicktime template
        """
        if self.get_batch_quicktime_template() is None:
            raise TankError("%s: Cannot evaluate quicktime path because no "
                            "batch quicktime template has been defined." % self)
        
        render_template = self.get_batch_render_template()
        fields = render_template.get_fields(batch_render_path)
        # plug in the fields into the quicktime template
        batch_quicktime_template = self.get_batch_quicktime_template()
        return batch_quicktime_template.apply_fields(fields)      
        
        
    def quicktime_path_from_render_path(self, render_path):
        """
        Given a render path, generate a quicktime path.
        This will break up the render path in template fields given by
        the render template and then use those fields to create 
        a quicktime path.
        
        Note! This method means that the fields of the quicktime path
        need to be a subset of the fields available via the render path.
        
        This is because we don't always have access to the raw metadata fields that
        were originally used to compose the render path; for example when the batch
        render hooks trigger, all we have access to is the raw render path.
        
        :path render_path: A render path associated with this preset
        :returns: Path to a quicktime, resolved via the quicktime template  
        """
        
        if self.get_quicktime_template() is None:
            raise TankError("%s: Cannot evaluate quicktime path because no "
                            "quicktime template has been defined." % self)
        
        render_template = self.get_render_template()
        fields = render_template.get_fields(render_path)
        # plug in the fields into the quicktime template
        quicktime_template = self.get_quicktime_template()
        return quicktime_template.apply_fields(fields)      
    
    def get_quicktime_publish_type(self):
        """
        :returns: The publish type to use for quicktimes
        """
        return self._raw_preset["quicktime_publish_type"]
    
    def get_quicktime_publish_name(self, path):
        """
        Generate a name suitable for a publish.
        
        :param path: Path to generate name for
        :returns: A name suitable for a render publish
        """
        return self.__get_publish_name(self.get_quicktime_template(), path)        
    
    def upload_quicktime(self):
        """
        Indicates that quicktimes should be pushed to Shotgun.
        
        :returns: bool flag, true if quicktimes should be uploaded, false if not
        """
        return self._raw_preset["upload_quicktime"]
    
    ############################################################################################################
    # values relating to the export in general
    
    def get_xml_path(self):
        """
        Generate Flame export profile settings suitable for generating image sequences
        for all shots. This will return a path on disk where an xml export preset is located.
        
        This preset is combined by loading various sources - some of the main scaffold
        xml is in this file, the export dpx plate presets are loaded in via a hook, paths
        are converted from toolkit templates and resolved.
        
        :returns: path to export preset xml file
        """

        # first convert all relevant templates to Flame specific form        
        resolved_flame_templates = self.__resolve_flame_templates()
        
        # execute a hook to retrieve all the graphic settings
        # the video template passed down to the hook is escaped 
        # so that its special characters don't interfere with the xml markup
        escaped_video_name_pattern = cgi.escape(resolved_flame_templates["plate_template"])
        video_preset_xml = self._app.execute_hook_method("settings_hook", 
                                                         "get_video_preset", 
                                                         preset_name=self.get_name(), 
                                                         name_pattern=escaped_video_name_pattern, 
                                                         publish_linked=True)
        
        # now merge the video portion into a larger xml chunk which will be 
        # the export preset that we pass to Flame. 
        #
        # a note on xml file formats: 
        # Each major version of Flame typically implements a particular 
        # version of the preset xml protocol. This is denoted by a preset version
        # number in the xml file. In order for the integration to run smoothly across
        # multiple versions of Flame, Flame ideally needs to be presented with a preset
        # which matches the current preset version. If you present an older version, a
        # warning dialog may pop up which is confusing to users. Therefore, make sure that
        # we always generate xmls with a matching preset version.   
        preset_version = self._app.engine.preset_version
        
        xml = """<?xml version="1.0" encoding="UTF-8"?>
            <preset version="%s">
               <type>sequence</type>
               <comment>Export profile for the Shotgun Flame export</comment>
               <sequence>
                  <fileType>NONE</fileType>
                  <namePattern />
                  <includeVideo>True</includeVideo>
                  <exportVideo>True</exportVideo>
                  <videoMedia>
                     <mediaFileType>image</mediaFileType>
                     <commit>Original</commit>
                     <flatten>NoChange</flatten>
                     <exportHandles>True</exportHandles>
                     <nbHandles>{FRAME_HANDLES}</nbHandles>
                  </videoMedia>
                  <includeAudio>True</includeAudio>
                  <exportAudio>False</exportAudio>
                  <audioMedia>
                     <mediaFileType>audio</mediaFileType>
                     <commit>Original</commit>
                     <flatten>NoChange</flatten>
                     <exportHandles>True</exportHandles>
                     <nbHandles>{FRAME_HANDLES}</nbHandles>
                  </audioMedia>
               </sequence>

               {VIDEO_EXPORT_PRESET}

               <name>
                  <framePadding>{FRAME_PADDING}</framePadding>
                  <useTimecode>{USE_TIMECODE}</useTimecode>
               </name>
               <createOpenClip>
                  <namePattern>{SEGMENT_CLIP_NAME_PATTERN}</namePattern>
                  <version>
                     <index>0</index>
                     <padding>{VERSION_PADDING}</padding>
                     <name>v&lt;version&gt;</name>
                  </version>
                  <batchSetup>
                     <namePattern>{BATCH_NAME_PATTERN}</namePattern>
                     <exportNamePattern>{SHOT_CLIP_NAME_PATTERN}</exportNamePattern>
                     <outputPathPattern>{OUTPUT_PATH_PATTERN}</outputPathPattern>
                  </batchSetup>
               </createOpenClip>
               <reImport>
                  <namePattern />
               </reImport>
            </preset>
        """ % preset_version

        # wedge in the video settings we got from the hook
        xml = xml.replace("{VIDEO_EXPORT_PRESET}", video_preset_xml)

        # and simple data type settings
        xml = xml.replace("{FRAME_HANDLES}", str(self._raw_preset["frame_handles"]))

        # now perform substitutions based on the rest of the resolved Flame templates
        # make sure we escape any < and > before we add them to the xml
        xml = xml.replace("{SEGMENT_CLIP_NAME_PATTERN}", cgi.escape(resolved_flame_templates["segment_clip_template"]))
        xml = xml.replace("{BATCH_NAME_PATTERN}", cgi.escape(resolved_flame_templates["batch_template"]))
        xml = xml.replace("{SHOT_CLIP_NAME_PATTERN}", cgi.escape(resolved_flame_templates["shot_clip_template"]))
        xml = xml.replace("{OUTPUT_PATH_PATTERN}", cgi.escape(resolved_flame_templates["batch_render_template"]))

        # now adjust some parameters in the export xml based on the template setup.
        template = self.get_render_template()
        
        def get_padding_from_key(key, default):
            """
            Convert a key format spec into a padding that can be used in flame
            export preset.  The format spec is something like "04" for 0
            prefixed 4 digit padding.
            """
            if key is None:
                return str(default)
            if key.format_spec[0] != "0":
                return "1"
            return key.format_spec.lstrip("0")

        # First up is the padding for sequences
        # (use flame.frame token first else fallback on SEQ for legacy configs)
        frame_token = "flame.frame"
        sequence_key = template.keys.get(frame_token)
        if sequence_key is None:
            frame_token = "SEQ"
            sequence_key = template.keys.get(frame_token)

        frame_padding = get_padding_from_key(key=sequence_key, default="4")
        xml = xml.replace("{FRAME_PADDING}", frame_padding)
        self._app.log_debug("Flame preset generation: Setting frame padding to %s based on "
                            "%s token in template %s" % (frame_padding, frame_token, template))

        use_timecode = str(self._raw_preset.get("use_timecode_as_frame_number", True))
        xml = xml.replace("{USE_TIMECODE}", str(use_timecode))
        self._app.log_debug("Flame preset generation: Setting use timecode to %s based on "
                            "%s token in template %s" % (use_timecode, frame_token, template))

        # Align the padding for versions with the definition in the version template
        version_key = template.keys.get("version")
        vesion_padding = get_padding_from_key(key=version_key, default="3")
        xml = xml.replace("{VERSION_PADDING}", vesion_padding)
        self._app.log_debug("Flame preset generation: Setting version padding to %s based on "
                            "version token in template %s" % (vesion_padding, template))

        # write it to disk
        preset_path = self.__write_content_to_file(xml, "export_preset.xml")

        return preset_path

    ###############################################################################################
    # helper methods and internals
    
    def __write_content_to_file(self, content, file_name):
        """
        Helper method. Writes content to file and returns the path.
        The content will be written to the app specific cache location 
        on disk, organized by app instance name. The rationale is that 
        each app instance holds its own configuration, and the configuration
        generates one set of unique xml files.
        
        :param content: Data to write to the file
        :param file_name: The name of the file to create
        :returns: path to the created file
        """
        # determine location
        file_path = os.path.join(self._app.cache_location, self._app.instance_name, file_name)
        folder = os.path.dirname(file_path)

        # create folders
        if not os.path.exists(folder):
            old_umask = os.umask(0)
            os.makedirs(folder, 0777)
            os.umask(old_umask)
        
        # write data
        fh = open(file_path, "wt")
        fh.write(content)
        fh.close()
        
        self._app.log_debug("Wrote temporary file '%s'" % file_path)
        return file_path

    def __resolve_flame_templates(self):
        """
        Convert the toolkit templates defined in the app settings to 
        Flame equivalents.
        
        :returns: Dictionary of Flame template definition strings, keyed by
                  the same names as are being used for the templates in the app settings.
        """
        # now we need to take our toolkit templates and inject them into the xml template
        # definition that we are about to send to Flame.
        #
        # typically, our template defs will look something like this:
        # plate:        'sequences/{Sequence}/{Shot}/editorial/plates/{segment_name}_{Shot}.v{version}.{SEQ}.dpx'
        # batch:        'sequences/{Sequence}/{Shot}/editorial/flame/batch/{Shot}.v{version}.batch'
        # segment_clip: 'sequences/{Sequence}/{Shot}/editorial/flame/sources/{segment_name}.clip'
        # shot_clip:    'sequences/{Sequence}/{Shot}/editorial/flame/{Shot}.clip'
        #
        # {Sequence} may be {Scene} or {CustomEntityXX} according to the configuration and the 
        # exact entity type to use is passed into the hook via the the shot_parent_entity_type setting.
        #
        # The Flame export root is set to correspond to the toolkit project, meaning that both the 
        # Flame and toolkit templates share the same root point.
        #
        # The following replacements will be made to convert the toolkit template into Flame equivalents:
        # 
        # {Sequence}     ==> <name> (Note: May be {Scene} or {CustomEntityXX} according to the configuration)
        # {Shot}         ==> <shot name>
        # {segment_name} ==> <segment name>
        # {version}      ==> <version>
        # {SEQ}          ==> <frame>
        # {flame.frame}  ==> <frame>
        # 
        # and the special one <ext> which corresponds to the last part of the template. In the examples above:
        # {segment_name}_{Shot}.v{version}.{SEQ}.dpx : <ext> is '.dpx' 
        # {Shot}.v{version}.batch : <ext> is '.batch'
        # etc.
        #
        # example substitution:
        #
        # Toolkit: 'sequences/{Sequence}/{Shot}/editorial/plates/{segment_name}_{Shot}.v{version}.{SEQ}.dpx'
        #
        # Flame:   'sequences/<name>/<shot name>/editorial/plates/<segment name>_<shot name>.v<version>.<frame><ext>'
        #
        #
        shot_parent_entity_type = self._app.get_setting("shot_parent_entity_type")
        
        # get the export template defs for all our templates
        # the definition is a string on the form 
        # 'sequences/{Sequence}/{Shot}/editorial/plates/{segment_name}_{Shot}.v{version}.{SEQ}.dpx'
        template_defs = {}
        template_defs["plate_template"] = self.get_render_template().definition
        template_defs["batch_render_template"] = self.get_batch_render_template().definition
        template_defs["batch_template"] = self._app.get_template("batch_template").definition        
        template_defs["shot_clip_template"] = self._app.get_template("shot_clip_template").definition
        template_defs["segment_clip_template"] = self._app.get_template("segment_clip_template").definition
        
        # perform substitutions
        self._app.log_debug("Performing Toolkit -> Flame template field substitutions:")
        for t in template_defs:
            
            self._app.log_debug("Processing template %s" % t)
            self._app.log_debug("   Toolkit: %s" % template_defs[t])
            
            template_defs[t] = template_defs[t].replace("{%s}" % shot_parent_entity_type, "<name>")
            template_defs[t] = template_defs[t].replace("{Shot}", "<shot name>")
            template_defs[t] = template_defs[t].replace("{segment_name}", "<segment name>")
            template_defs[t] = template_defs[t].replace("{version}", "<version>")
            
            template_defs[t] = template_defs[t].replace("{SEQ}", "<frame>")
            template_defs[t] = template_defs[t].replace("{flame.frame}", "<frame>")
            
            template_defs[t] = template_defs[t].replace("{YYYY}", "<YYYY>")
            template_defs[t] = template_defs[t].replace("{MM}", "<MM>")
            template_defs[t] = template_defs[t].replace("{DD}", "<DD>")
            template_defs[t] = template_defs[t].replace("{hh}", "<hh>")
            template_defs[t] = template_defs[t].replace("{mm}", "<mm>")
            template_defs[t] = template_defs[t].replace("{ss}", "<ss>")
            template_defs[t] = template_defs[t].replace("{width}", "<width>")
            template_defs[t] = template_defs[t].replace("{height}", "<height>")
                        
            # Now carry over the sequence token
            (head, _) = os.path.splitext(template_defs[t])
            template_defs[t] = "%s<ext>" % head                        
            
            self._app.log_debug("   Flame:  %s" % template_defs[t])
        
        return template_defs

    
    
    
    
        
class ExportPresetHandler(object):
    """
    Manager class which wraps around the plate_presets configuration structure.
    
    This manager returns ExportPreset objects which contain the actual settings 
    and methods relating to a preset.
    """

    def __init__(self):
        """
        Constructor
        """
        self._app = sgtk.platform.current_bundle()
        
        raw_preset_data = self._app.get_setting("plate_presets")
        self._app.log_debug("ExportPresetHandler loaded export preset data "
                        "from environment: %s" % pprint.pformat(raw_preset_data))
        
        # create export preset objects
        self._export_presets = {}
        for raw_preset in raw_preset_data:
            preset_name = raw_preset["name"]
            self._export_presets[preset_name] = ExportPreset(raw_preset)
        
    def get_preset_names(self):
        """
        Returns all the export preset names defined in the environment.
        
        :returns: list of export preset strings 
        """
        raw_preset_data = self._app.get_setting("plate_presets")

        preset_names = []

        for raw_preset in raw_preset_data:
            preset_min_version = raw_preset.get("min_version", "0")

            if sgtk.platform.current_engine().is_version_less_than(preset_min_version):
                continue

            preset_names.append(raw_preset["name"])

        return sorted(preset_names)


    def get_preset_by_name(self, preset_name):
        """
        Returns an export preset given a preset name.
        
        
        :param preset_name: Name of export preset to retrieve. 
                            Use get_preset_names() to get names of available presets.
        :raises: TankError if preset is not found
        :returns: ExportPreset object
        """
        if preset_name not in self._export_presets:
            raise TankError("Export preset manager cannot find preset '%s' in the configuration!" % preset_name)
        
        return self._export_presets[preset_name]
    
    def get_preset_for_batch_render_path(self, path):
        """
        Given a path to an exported render, try to figure out which export preset was used to generate the path.
        
        This is useful for example in batch mode, where you no longer have access to the original settings.
        All you have access to at this point is the generated path, which is passed from Flame.
        
        :param path: Path to a render.
        :returns: None if no match could be established, otherwise an ExportPreset object
        """
        
        self._app.log_debug("Trying to locate an export preset "
                            "for batch render path '%s'..." % path)
        matching_preset = None
        for preset_obj in self._export_presets.values():

            template = preset_obj.get_batch_render_template()
            if template.validate(path):
                self._app.log_debug(" - Matching: '%s'" % preset_obj)
                matching_preset = preset_obj
                break
            else:
                self._app.log_debug(" - Not matching: '%s'" % preset_obj)

        return matching_preset
        
        



