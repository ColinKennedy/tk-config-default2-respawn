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

HookBaseClass = sgtk.get_hook_baseclass()


class ExportSettings(HookBaseClass):
    """
    This hook controls the settings that Flame will use when it exports plates and generates 
    quicktimes prior to uploading them to Shotgun.
    """

    def get_video_preset(self, preset_name, name_pattern, publish_linked):
        """
        Returns a chunk of video xml export profile given a preset name.
        This chunk of XML will be joined into a larger structure which defines
        the entire set of export options. The app will then pass this full preset
        to Flame for file generation.
        
        The preset name should correspond to one of the presets defined in the app
        config - for each of these presets, this hook needs to implement logic to 
        handle that preset. 
        
        Certain fields should be populated with particular data from the system.
        These 'dynamic fields' will get values via the input parameters of this method.
        
        :param preset_name: The name of the export preset that the user has selected in the 
                            export UI dialog.
        :param name_pattern: Data to inject into the <name_pattern> tag in the xml structure.
        :param publish_linked: Data to inject into the <publishLinked> tag in the xml structure.
        
        :returns: the <video> xml section of a Flame export.
        """
        if preset_name == "10 bit DPX":

            # The codec ids have changed between flame 2016 and 2017
            preset_version_str = self.parent.engine.preset_version
            preset_version = int(preset_version_str)
            codec_id = 923680 if preset_version < 7 else 6176

            xml = """
                   <video>
                      <fileType>Dpx</fileType>
                      <codec>%d</codec>
                      <codecProfile />
                      <namePattern>{VIDEO_NAME_PATTERN}</namePattern>
                      <compressionQuality>50</compressionQuality>
                      <transferCharacteristic>2</transferCharacteristic>
                      <colorimetricSpecification>4</colorimetricSpecification>
                      <publishLinked>{PUBLISH_LINKED}</publishLinked>
                      <foregroundPublish>False</foregroundPublish>
                      <overwriteWithVersions>False</overwriteWithVersions>
                      <resize>
                         <resizeType>fit</resizeType>
                         <resizeFilter>lanczos</resizeFilter>
                         <width>0</width>
                         <height>0</height>
                         <bitsPerChannel>10</bitsPerChannel>
                         <numChannels>3</numChannels>
                         <floatingPoint>False</floatingPoint>
                         <bigEndian>True</bigEndian>
                         <pixelRatio>1</pixelRatio>
                         <scanFormat>P</scanFormat>
                      </resize>
                   </video>
                """ % codec_id
            
        elif preset_name == "16 bit OpenEXR":
            xml = """
                   <video>
                      <fileType>OpenEXR</fileType>
                      <codec>596088</codec>
                      <codecProfile />
                      <namePattern>{VIDEO_NAME_PATTERN}</namePattern>
                      <compressionQuality>50</compressionQuality>
                      <transferCharacteristic>2</transferCharacteristic>
                      <colorimetricSpecification>4</colorimetricSpecification>
                      <publishLinked>{PUBLISH_LINKED}</publishLinked>
                      <foregroundPublish>False</foregroundPublish>
                      <overwriteWithVersions>False</overwriteWithVersions>
                      <resize>
                         <resizeType>fit</resizeType>
                         <resizeFilter>lanczos</resizeFilter>
                         <width>0</width>
                         <height>0</height>
                         <bitsPerChannel>16</bitsPerChannel>
                         <numChannels>3</numChannels>
                         <floatingPoint>True</floatingPoint>
                         <bigEndian>False</bigEndian>
                         <pixelRatio>1</pixelRatio>
                         <scanFormat>P</scanFormat>
                      </resize>
                   </video>
                """
        elif preset_name == "16 bit OpenEXR - Multi-Channel":
            xml = """
                   <video>
                      <fileType>OpenEXR</fileType>
                      <codec>596088</codec>
                      <codecProfile></codecProfile>
                      <namePattern>{VIDEO_NAME_PATTERN}</namePattern>
                      <compressionQuality>50</compressionQuality>
                      <transferCharacteristic>2</transferCharacteristic>
                      <colorimetricSpecification>4</colorimetricSpecification>
                      <multiTrack>True</multiTrack>
                      <overwriteWithVersions>False</overwriteWithVersions>
                      <resize>
                         <resizeType>fit</resizeType>
                         <resizeFilter>lanczos</resizeFilter>
                         <width>0</width>
                         <height>0</height>
                         <bitsPerChannel>16</bitsPerChannel>
                         <numChannels>3</numChannels>
                         <floatingPoint>True</floatingPoint>
                         <bigEndian>False</bigEndian>
                         <pixelRatio>1</pixelRatio>
                         <scanFormat>P</scanFormat>
                      </resize>
                   </video>

                """
        else:
            raise TankError("Unknown video export preset '%s'!" % preset_name)
        
        xml = xml.replace("{VIDEO_NAME_PATTERN}", name_pattern)
        xml = xml.replace("{PUBLISH_LINKED}", str(publish_linked))
        
        return xml
