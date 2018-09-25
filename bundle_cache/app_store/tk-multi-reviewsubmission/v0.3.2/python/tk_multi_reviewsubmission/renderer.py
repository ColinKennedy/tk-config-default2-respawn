# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
import os
import sys
import nuke

class Renderer(object):
    
    def __init__(self):
        """
        Construction
        """
        self.__app = sgtk.platform.current_bundle() 
        
        self._burnin_nk = os.path.join(self.__app.disk_location, "resources", "burnin.nk")
        self._font = os.path.join(self.__app.disk_location, "resources", "liberationsans_regular.ttf")
        
        # If the slate_logo supplied was an empty string, the result of getting 
        # the setting will be the config folder which is invalid so catch that
        # and make our logo path an empty string which Nuke won't have issues with.
        self._logo = None
        if os.path.isfile( self.__app.get_setting("slate_logo", "") ):
            self._logo = self.__app.get_setting("slate_logo", "")
        else:
            self._logo = ""

        # now transform paths to be forward slashes, otherwise it wont work on windows.
        if sys.platform == "win32":
            self._font = self._font.replace(os.sep, "/")
            self._logo = self._logo.replace(os.sep, "/")
            self._burnin_nk = self._burnin_nk.replace(os.sep, "/") 

    def render_movie_in_nuke(self, path, output_path, 
                             width, height, 
                             first_frame, last_frame, 
                             version, name, 
                             color_space):
        """
        Use Nuke to render a movie. This assumes we're running _inside_ Nuke.
                        
        :param path:        Path to the input frames for the movie
        :param output_path: Path to the output movie that will be rendered
        :param width:       Width of the output movie
        :param height:      Height of the output movie
        :param first_frame: Start frame for the output movie
        :param last_frame:  End frame for the output movie
        :param version:     Version number to use for the output movie slate and burn-in
        :param name:        Name to use in the slate for the output movie
        :param color_space: Colorspace of the input frames
        """
        output_node = None
        ctx = self.__app.context

        # create group where everything happens
        group = nuke.nodes.Group()
        
        # now operate inside this group
        group.begin()
        try:
            # create read node
            read = nuke.nodes.Read(name="source", file=path.replace(os.sep, "/"))
            read["on_error"].setValue("black")
            read["first"].setValue(first_frame)
            read["last"].setValue(last_frame)
            if color_space:
                read["colorspace"].setValue(color_space)
            
            # now create the slate/burnin node
            burn = nuke.nodePaste(self._burnin_nk) 
            burn.setInput(0, read)
        
            # set the fonts for all text fields
            burn.node("top_left_text")["font"].setValue(self._font)
            burn.node("top_right_text")["font"].setValue(self._font)
            burn.node("bottom_left_text")["font"].setValue(self._font)
            burn.node("framecounter")["font"].setValue(self._font)
            burn.node("slate_info")["font"].setValue(self._font)
        
            # add the logo
            burn.node("logo")["file"].setValue(self._logo)
            
            # format the burnins
            version_padding_format = "%%0%dd" % self.__app.get_setting("version_number_padding")
            version_str = version_padding_format % version
            
            if ctx.task:
                version_label = "%s, v%s" % (ctx.task["name"], version_str)
            elif ctx.step:
                version_label = "%s, v%s" % (ctx.step["name"], version_str)
            else:
                version_label = "v%s" % version_str
            
            burn.node("top_left_text")["message"].setValue(ctx.project["name"])
            burn.node("top_right_text")["message"].setValue(ctx.entity["name"])
            burn.node("bottom_left_text")["message"].setValue(version_label)
            
            # and the slate            
            slate_str =  "Project: %s\n" % ctx.project["name"]
            slate_str += "%s: %s\n" % (ctx.entity["type"], ctx.entity["name"])
            slate_str += "Name: %s\n" % name.capitalize()
            slate_str += "Version: %s\n" % version_str
            
            if ctx.task:
                slate_str += "Task: %s\n" % ctx.task["name"]
            elif ctx.step:
                slate_str += "Step: %s\n" % ctx.step["name"]
            
            slate_str += "Frames: %s - %s\n" % (first_frame, last_frame)
            
            burn.node("slate_info")["message"].setValue(slate_str)

            # create a scale node
            scale = self.__create_scale_node(width, height)
            scale.setInput(0, burn)                

            # Create the output node
            output_node = self.__create_output_node(output_path)
            output_node.setInput(0, scale)
        finally:
            group.end()
    
        if output_node:
            # Make sure the output folder exists
            output_folder = os.path.dirname(output_path)
            self.__app.ensure_folder_exists(output_folder)
            
            # Render the outputs, first view only
            nuke.executeMultiple([output_node], ([first_frame-1, last_frame, 1],), [nuke.views()[0]])

        # Cleanup after ourselves
        nuke.delete(group)
        
        
    def __create_scale_node(self, width, height):
        """
        Create the Nuke scale node to resize the content.
        """
        scale = nuke.nodes.Reformat()
        scale["type"].setValue("to box")
        scale["box_width"].setValue(width)
        scale["box_height"].setValue(height)
        scale["resize"].setValue("fit")
        scale["box_fixed"].setValue(True)
        scale["center"].setValue(True)
        scale["black_outside"].setValue(True)
        return scale

    def __create_output_node(self, path):
        """
        Create the Nuke output node for the movie.
        """
        # get the Write node settings we'll use for generating the Quicktime
        wn_settings = self.__app.execute_hook_method("codec_settings_hook", 
                                                     "get_quicktime_settings")

        node = nuke.nodes.Write(file_type=wn_settings.get("file_type"))
        
        # apply any additional knob settings provided by the hook. Now that the knob has been 
        # created, we can be sure specific file_type settings will be valid.
        for knob_name, knob_value in wn_settings.iteritems():
            if knob_name != "file_type":
                node.knob(knob_name).setValue(knob_value)
        
        # Don't fail if we're in proxy mode. The default Nuke publish will fail if
        # you try and publish while in proxy mode. But in earlier versions of 
        # tk-multi-publish (< v0.6.9) if there is no proxy template set, it falls 
        # back on the full-res version and will succeed. This handles that case
        # and any custom cases where you may want to send your proxy render to 
        # screening room. 
        root_node = nuke.root()
        is_proxy = root_node['proxy'].value()
        if is_proxy:
            self.__app.log_info("Proxy mode is ON. Rendering proxy.")
            node["proxy"].setValue(path.replace(os.sep, "/"))
        else:
            node["file"].setValue(path.replace(os.sep, "/"))

        return node  