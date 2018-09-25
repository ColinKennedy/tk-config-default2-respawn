# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

__all__ = ["Transcoder"]

import os
import tempfile

from sgtk import TankError

class Transcoder(object):
    """
    Thumbnail generator based on Flame export API
    """

    def __init__(self, engine):
        self._engine = engine

    @property
    def engine(self):
        """
        :returns the DCC engine:
        """
        return self._engine

    def _import_clip(self, path):
        """
        Imports a single clip at a given path.

        :param path: Path to the media to import.
        :returns clip: Flame's Python API clip object or none.
        """
        import flame
        clips = flame.import_clips(path)
        self.engine.log_debug("Imported '%s' -> [%s]" % (path, clips))
        if len(clips) == 0:
            self.engine.log_warning("%s does not points to a clip" % path)
            return None
        elif len(clips) > 1:
            self.engine.log_warning("%s points to more than one clip." \
                                    " First one will be used." % path)
        return clips[0]

    @staticmethod
    def _build_python_hook_override(user_data_job_key):
        """
        Build a Flame's python hook override callback for export that will
        prevent python hook to trigger a shotgun publish when generating the
        thumbnails from the Flame's export API.

        Also collect the background job create if any and flag that we want to
        overwrite any media exported.

        :param user_data_job_key: Key to use in userData for the background job
            ID collected.
        :returns PythonHookOverride: Python Hook override callback object.
        """

        class PythonHookOverride(object):
            def __init__(self, user_data_job_key):
                self._user_data_job_key = user_data_job_key

            def preExport(self, info, userData, *args, **kwargs):
                pass

            def postExport(self, info, userData, *args, **kwargs):
                pass

            def preExportSequence(self, info, userData, *args, **kwargs):
                pass

            def postExportSequence(self, info, userData, *args, **kwargs):
                pass

            def preExportAsset(self, info, userData, *args, **kwargs):
                pass

            def postExportAsset(self, info, userData, *args, **kwargs):
                userData[self._user_data_job_key] = info["backgroundJobId"]

            def exportOverwriteFile(self, path, *args, **kwargs):
                return "overwrite"
        return PythonHookOverride(user_data_job_key)

    def _create_temporary_file(self, extension, clip):
        """
        Create a temporary file and rename the clip to match to the file name
        so the clip, once exported will overwrite that file.

        :param extension: Extension of the temporary file created
        :param clip: Flame's clip object we want to rename to match the
            temporary file created.
        :returns path: String of the path created.
        """
        (tmp_fd, path) = tempfile.mkstemp(
            suffix=extension,
            dir=self.engine.get_backburner_tmp())
        os.close(tmp_fd)
        clip.name = os.path.splitext(os.path.basename(path))[0]
        return path

    def _create_open_clip_file(self, src_path, asset_info):
        """
        Create an Open Clip file that points to the exported asset that can
        be used to import the clip before it is actually finished exporting.

        This can be used to schedule an export job depending on another export
        job before the first one complete.

        :param src_path: Path to the media for which transcoding need to be done.
        :param asset_info: Dictionary of attribute passed by Flame's python
            hooks collected either thru an export (sg_export_hooks.py) or a
            batch render (sg_batch_hooks.py).

        :returns path: String of the path created, None in case of error.
        """
        if asset_info["assetType"] not in ["video", "movie"]:
            self.engine.log_error("Cannot create Open clip for non-video assets")
            return None

        (tmp_fd, path) = tempfile.mkstemp(
            suffix=".clip",
            dir=self.engine.get_backburner_tmp())

        metadata = {}
        metadata["path"] = src_path
        metadata["height"] = asset_info["height"]
        metadata["width"] = asset_info["width"]
        channels_encoding = asset_info.get("channelsEncoding", None)
        if channels_encoding is None:
            channels_encoding = "Float" if "fp" in asset_info["depth"] else "Integer"
        metadata["channelsEncoding"] = channels_encoding
        metadata["channelsDepth"] = asset_info["depth"].replace("-bit", "").replace(" fp", "")
        metadata["pixelLayout"] = asset_info.get("pixelLayout", "RGB")
        metadata["nbChannels"] = len(metadata["pixelLayout"])
        try:
            metadata["pixelRatio"] = asset_info.get("aspectRatio", 1.0) \
                                   * asset_info["height"] / asset_info["width"]
        except ZeroDivisionError:
            metadata["pixelRatio"] = 1.0

        scan_format = asset_info.get("scanFormat", "PROGRESSIVE")
        if scan_format == "FIELD_1":
            metadata["fieldDominance"] = 0
        if scan_format == "FIELD_2":
            metadata["fieldDominance"] = 1
        else: # PROGRESSIVE
            metadata["fieldDominance"] = 2
        metadata["colourSpace"] = asset_info.get("colourSpace", "Unknown")

        try:
            source_in = int(asset_info.get("sourceIn", 0))
            source_out = int(asset_info.get("sourceOut", source_in + 1))
            nb_frames = source_out - source_in
            metadata["duration"] = "<duration>%d</duration>" % (nb_frames)
        except:
            metadata["duration"] = ""

        metadata["sampleRate"] = asset_info.get("fps")

        extension = os.path.splitext(src_path)[1].lower()
        handlers = {
            ".mov": "Quicktime"
        }
        handler = handlers.get(extension, None)
        if handler is not None:
            metadata["handler"] = "<handler><name>%s</name></handler>" % handler
        else:
            metadata["handler"] = ""

        os.write(
            tmp_fd,
            """
            <clip type=\"clip\" version=\"4\">
             <tracks type=\"tracks\">
              <track type=\"track\" uid=\"t0\">
               <trackType>video</trackType>
               <feeds currentVersion=\"v0\">
                <feed type=\"feed\" vuid=\"v0\" uid=\"v0\">
                 {handler}
                 <storageFormat type=\"format\">
                  <type>video</type>
                  <nbChannels type=\"uint\">{nbChannels}</nbChannels>
                  <channelsDepth type=\"uint\">{channelsDepth}</channelsDepth>
                  <channelsEncoding type=\"string\">{channelsEncoding}</channelsEncoding>
                  <pixelLayout type=\"string\">{pixelLayout}</pixelLayout>
                  <height type=\"uint\">{height}</height>
                  <pixelRatio type=\"float\">{pixelRatio}</pixelRatio>
                  <width type=\"uint\">{width}</width>
                  <fieldDominance type=\"int\">{fieldDominance}</fieldDominance>
                  <colourSpace type=\"string\">{colourSpace}</colourSpace>
                 </storageFormat>
                 <sampleRate>{sampleRate}</sampleRate>
                 <spans type=\"spans\">
                  <span type=\"span\">
                   {duration}
                   <path encoding=\"pattern\">{path}</path>
                  </span>
                 </spans>
                </feed>
               </feeds>
              </track>
             </tracks>
            </clip>""".format(**metadata))
        os.close(tmp_fd)
        return path

    def transcode(self, src_path, dst_path, extension, display_name, job_context, preset_path, asset_info, dependencies, poster_frame=None):
        """
        Generate a preview for a given media asset and link
        it to a list of Shotgun entities. Multiple call to this method with
        same path but different target_entitie can be done to bundle jobs.

        :param src_path: Path to the media for which transcoding need to be done.
        :param dst_path: Path of the trancoded media.
        :param display_name: The display name of the item we are generating the
            thumbnail for. This will usually be the based name of the path.
        :param preset_path: The path to the preset to use to export the movie file.
        :param asset_info: Dictionary of attribute passed by Flame's python
            hooks collected either thru an export (sg_export_hooks.py) or a
            batch render (sg_batch_hooks.py).
        :param dependencies: List of backburner job IDs this thumbnail
            generation job need to wait in order to be started. Can be None if
            the media is created in foreground.
        """

        import flame
        temp_files = []

        # If we depend on a backburner jobs we cannot reimport the exported
        # media until it finished exporting, however we would like to send the
        # transcoding job before that happen. We can however create an Open Clip
        # file that point to the exported media location with the matching
        # metadata and import it. Reading the frames on that Open Clip would
        # fail before the original export job is finished but since the thumbnail
        # transcoding job depend on it, it will be fine by then.
        #
        if dependencies is not None:
            if os.path.splitext(src_path)[-1].lower() != ".clip":
                path_to_import = self._create_open_clip_file(
                    src_path=src_path,
                    asset_info=asset_info
                )
                temp_files.append(path_to_import)
            else:
                path_to_import = src_path
        else:
            path_to_import = src_path
        clip = self._import_clip(path=path_to_import)
        if clip is None:
            raise TankError(
                "%s cannot be imported to be transcoded." % path_to_import
            )


        if dst_path is None:
            actual_dst_path = self._create_temporary_file(
                extension=extension,
                clip=clip
            )
            temp_files.append(actual_dst_path)
        else:
            actual_dst_path = dst_path

        exporter = flame.PyExporter()
        exporter.foreground_export = False

        # FIXME this will work only if out_mark is exclusive which is the default.
        if poster_frame is not None:
            clip.in_mark = poster_frame
            clip.out_mark = poster_frame + 1
            exporter.export_between_marks = True

        self.engine.log_debug("Exporting using preset '%s' to '%s' depending on '%s'" % \
                              (preset_path, actual_dst_path, dependencies))

        background_job_settings = flame.PyExporter.BackgroundJobSettings()
        background_job_settings.name = "%s - %s" % (
            display_name,
            job_context
        )
        background_job_settings.description = "%s for %s - %s -> %s" % (
            job_context,
            display_name,
            src_path,
            dst_path
        )
        background_job_settings.dependencies = dependencies

        hooks_user_data = {}
        transcoder_job_key = "transcoder_job"
        exporter.export(
            sources=clip,
            preset_path=preset_path,
            output_directory=self.engine.get_backburner_tmp(),
            background_job_settings=background_job_settings,
            hooks=self._build_python_hook_override(transcoder_job_key),
            hooks_user_data=hooks_user_data)
        return (actual_dst_path, hooks_user_data.get(transcoder_job_key), temp_files)
