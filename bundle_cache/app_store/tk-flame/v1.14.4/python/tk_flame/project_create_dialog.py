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
from sgtk.platform.qt import QtCore, QtGui
from .ui.project_create_dialog import Ui_ProjectCreateDialog

class ProjectCreateDialog(QtGui.QWidget):
    """
    Project setup dialog for Flame
    """

    # map the tab indices in the UI to constants
    (TAB_GENERAL, TAB_RESOLUTION, TAB_OLD_PROXY, TAB_NEW_PROXY) = range(4)

    def __init__(self,
                 project_name,
                 user_name,
                 workspace_name,
                 default_volume_name,
                 volume_names,
                 host_name,
                 default_group_name,
                 group_names,
                 project_settings):

        """
        Constructor

        :param project_name: Name of the project as string
        :param user_name: Name of the user as string
        :param workspace_name: Name of the workspace as string, None if default workspace should be used
        :param default_volume_name: The default volume name, as string
        :param volume_names: All available volumes, list of strings
        :param host_name: The host name to create the project on (str)
        :param project_settings: Project settings. Dictionary as returned by
                                 the project_startup_hook's get_project_settings method
        """
        # first, call the base class and let it do its thing.
        QtGui.QWidget.__init__(self)

        self._engine = sgtk.platform.current_bundle()

        # now load in the UI that was created in the UI designer
        self.ui = Ui_ProjectCreateDialog()
        self.ui.setupUi(self)

        # with the tk dialogs, we need to hook up our modal
        # dialog signals in a special way
        self.__exit_code = QtGui.QDialog.Rejected
        self.ui.create_project.clicked.connect(self._on_submit_clicked)
        self.ui.abort.clicked.connect(self._on_abort_clicked)

        # set up callbacks
        self.ui.help_link.linkActivated.connect(self._on_help_url_clicked)

        # populate fixed fields (the first tab)
        self.ui.project_name.setText(project_name)
        self.ui.setup_dir.setPlaceholderText("<default>")
        self.ui.user_name.setText(user_name)
        if workspace_name:
            self.ui.workspace_name.setText(workspace_name)
        else:
            self.ui.workspace_name.setText("Will use a Flame Default Workspace")
        self.ui.host_name.setText(host_name)

        # populate storage volume dropdown
        self.ui.volume.addItems(volume_names)
        # now select the default value in combo box
        idx = self.ui.volume.findText(default_volume_name)
        self.ui.volume.setCurrentIndex(idx)

        self.ui.group_name.addItems(group_names)
        idx = self.ui.group_name.findText(default_group_name)
        self.ui.group_name.setCurrentIndex(idx)

        if self._engine.is_version_less_than("2018.1"):
            # no security support in wiretap before 2018.1
            self.ui.group_name_label.setVisible(False)
            self.ui.group_name.setVisible(False)

            # no 32-bit fp support in wiretap before 2018.1
            self.ui.depth.removeItem(0)

        # populate the resolution tab
        self.__populate_resolution_tab(project_settings)

        # populate proxy tab
        if self._engine.is_version_less_than("2016.1"):
            # hide new-style settings tab
            self.ui.tabWidget.removeTab(self.TAB_NEW_PROXY)
            # init old-style settings tab
            self.__set_up_old_proxy_tab(project_settings)
        else:
            # hide old settings tab
            self.ui.tabWidget.removeTab(self.TAB_OLD_PROXY)
            # init new settings tab
            self.__set_up_new_proxy_tab(project_settings)

    def __populate_resolution_tab(self, project_settings):
        """
        Populate the resolution UI tab with values from
        the given project settings dictionary

        :param project_settings: Dictionary as returned by
                                 the project_startup_hook's get_project_settings method
        """
        # populate the resolution tab
        self.ui.width.setText(str(project_settings.get("FrameWidth")))
        self.ui.height.setText(str(project_settings.get("FrameHeight")))

        self.__set_combo_value(project_settings, self.ui.depth, "FrameDepth")
        self.__set_combo_value(project_settings, self.ui.field_dominance, "FieldDominance")
        self.__set_combo_value(project_settings, self.ui.frame_rate, "FrameRate")

        aspect_ratio = project_settings.get("AspectRatio")

        # aspect ratio: ["4:3", "16:9", "Based on width/height"]
        if aspect_ratio == "1.7778":
            self.ui.aspect_ratio.setCurrentIndex(1)
        elif aspect_ratio == "1.333":
            self.ui.aspect_ratio.setCurrentIndex(0)
        else:
            # use width/height aspect ratio
            self.ui.aspect_ratio.setCurrentIndex(2)

    def __set_up_old_proxy_tab(self, project_settings):
        """
        Populate the proxy UI tab with values from
        the given project settings dictionary. This method is for
        flame versions 2016.0 and below.

        :param project_settings: Dictionary as returned by
                                 the project_startup_hook's get_project_settings method
        """
        # set up signals for interaction
        self.ui.proxy_width_hint.valueChanged.connect(self._on_proxy_width_hint_change)
        self.ui.proxy_min_frame_size.valueChanged.connect(self._on_proxy_min_frame_size_change)
        self.ui.proxy_mode.currentIndexChanged.connect(self._on_proxy_mode_change)

        enable_proxy = project_settings.get("ProxyEnable") == "true"
        proxy_min_frame_size = int(project_settings.get("ProxyMinFrameSize") or 0)

        # first reset the combo to trigger the change events later
        self.ui.proxy_mode.setCurrentIndex(-1)

        if enable_proxy == False and proxy_min_frame_size == 0:
            self.ui.proxy_mode.setCurrentIndex(0) # off
        elif enable_proxy == False and proxy_min_frame_size > 0:
            self.ui.proxy_mode.setCurrentIndex(1) # conditionally
        else:
            self.ui.proxy_mode.setCurrentIndex(2) # on

        self.__set_combo_value(project_settings, self.ui.proxy_depth, "ProxyDepthMode")
        self.__set_combo_value(project_settings, self.ui.proxy_quality, "ProxyQuality")

        if project_settings.get("ProxyAbove8bits") == "true":
            self.ui.proxy_above_8_bits.setChecked(True)
        else:
            self.ui.proxy_above_8_bits.setChecked(False)

        pmfs = int(project_settings.get("ProxyMinFrameSize"))
        pwh = int(project_settings.get("ProxyWidthHint"))

        self.ui.proxy_width_hint.setValue(pwh)
        self.ui.proxy_min_frame_size.setValue(pmfs)


    def __set_up_new_proxy_tab(self, project_settings):
        """
        Populate the proxy UI tab with values from
        the given project settings dictionary. This method is for
        flame versions 2016.1 and above

        :param project_settings: Dictionary as returned by
                                 the project_startup_hook's get_project_settings method
        """
        # set the quality combo
        self.__set_combo_value(project_settings, self.ui.new_proxy_quality, "ProxyQuality")

        # set the checkbox
        if project_settings.get("ProxyRegenState") == "true":
            self.ui.new_generate_proxies.setChecked(True)
        else:
            self.ui.new_generate_proxies.setChecked(False)

        # set the minimum size slider
        proxy_min_frame_size = int(project_settings.get("ProxyMinFrameSize") or 0)
        self.ui.new_proxy_width.setValue(proxy_min_frame_size)

        # figure out the mode setting - this is driven by the ProxyWidth setting
        proxy_width = float(project_settings.get("ProxyWidthHint") or 0.0)

        if proxy_width == 0.5:
            combo_index = self.ui.new_proxy_mode.findText("Proxy 1/2")

        elif proxy_width == 0.25:
            combo_index = self.ui.new_proxy_mode.findText("Proxy 1/4")

        elif proxy_width == 0.125:
            combo_index = self.ui.new_proxy_mode.findText("Proxy 1/8")

        else:
            combo_index = self.ui.new_proxy_mode.findText("Proxy 1/2")

        self.ui.new_proxy_mode.setCurrentIndex(combo_index)

    def __set_combo_value(self, project_settings, combo_widget, setting):
        """
        Helper method.
        Given a settings value, set up a combo box
        """
        value = project_settings.get(setting)
        if value is None:
            # nothing selected
            combo_widget.setCurrentIndex(-1)
        else:
            idx = combo_widget.findText(str(value))
            combo_widget.setCurrentIndex(idx)

    def get_volume_name(self):
        """
        Returns the selected storage volume

        :returns: volume as string
        """
        return str(self.ui.volume.currentText())

    def get_group_name(self):
        """
        Returns the selected group

        :returns: group as string
        """
        return str(self.ui.group_name.currentText())

    def get_settings(self):
        """
        Returns a settings dictionary, on the following form:

         - FrameWidth (e.g. "1280")
         - FrameHeight (e.g. "1080")
         - FrameDepth (16-bit fp, 12-bit, 12-bit u, 10-bit, 8-bit)
         - FrameRate (23.976, 24, 25, 29.97 df, 29.97 ndf, 30, 50, 50.94 df, 50.94 ndf, 60)
         - FieldDominance (PROGRESSIVE, FIELD_1, FIELD_2)
         - AspectRatio (4:3, 16:9, or floating point value as string)

         - ProxyEnable ("true" or "false")
         - ProxyWidthHint
         - ProxyDepthMode
         - ProxyMinFrameSize
         - ProxyAbove8bits ("true" or "false")
         - ProxyQuality
         - ProxyRegenState
         - ProxyDepth
        """
        settings = {}

        setup_dir = self.ui.setup_dir.text().strip()
        if setup_dir:
            settings["SetupDir"] = setup_dir
        settings["FrameWidth"] = self.ui.width.text()
        settings["FrameHeight"] = self.ui.height.text()
        settings["FrameDepth"] = self.ui.depth.currentText()
        settings["FieldDominance"] = self.ui.field_dominance.currentText()
        settings["FrameRate"] = self.ui.frame_rate.currentText()

        # aspect ratio: ["4:3", "16:9", "Based on width/height"]

        if self.ui.aspect_ratio.currentIndex() == 0:
            settings["AspectRatio"] = "1.33333"
        elif self.ui.aspect_ratio.currentIndex() == 1:
            settings["AspectRatio"] = "1.777778"
        else:
            settings["AspectRatio"] = "%4f" % (float(settings["FrameWidth"]) / float(settings["FrameHeight"]))

        if self._engine.is_version_less_than("2016.1"):
            # old proxy settings
            if self.ui.proxy_mode.currentIndex() == 0:
                settings["ProxyEnable"] = "false"
                settings["ProxyWidthHint"] = "0"

            elif self.ui.proxy_mode.currentIndex() == 1:
                settings["ProxyEnable"] = "false"
                settings["ProxyWidthHint"] = "%s" % self.ui.proxy_width_hint.value()
                settings["ProxyDepthMode"] = self.ui.proxy_depth.currentText()
                settings["ProxyMinFrameSize"] = "%s" % self.ui.proxy_min_frame_size.value()
                settings["ProxyAbove8bits"] = "true" if self.ui.proxy_above_8_bits.isChecked() else "false"
                settings["ProxyQuality"] = self.ui.proxy_quality.currentText()

            else:
                settings["ProxyEnable"] = "true"
                settings["ProxyWidthHint"] = "%s" % self.ui.proxy_width_hint.value()
                settings["ProxyDepthMode"] = self.ui.proxy_depth.currentText()
                settings["ProxyMinFrameSize"] = "%s" % self.ui.proxy_min_frame_size.value()
                settings["ProxyAbove8bits"] = "true" if self.ui.proxy_above_8_bits.isChecked() else "false"
                settings["ProxyQuality"] = self.ui.proxy_quality.currentText()

        else:
            # new (2016.1 and above) proxy settings
            settings["ProxyRegenState"] = "true" if self.ui.new_generate_proxies.isChecked() else "false"
            settings["ProxyQuality"] = self.ui.new_proxy_quality.currentText()
            settings["ProxyMinFrameSize"] = "%s" % self.ui.new_proxy_width.value()

            # the ProxyWidthHint is derived from the 1/2, 1/4, 1/8 settings and the width
            if self.ui.new_proxy_mode.currentText() == "Proxy 1/2":
                settings["ProxyWidthHint"] = "0.5"

            elif self.ui.new_proxy_mode.currentText() == "Proxy 1/4":
                settings["ProxyWidthHint"] = "0.25"

            elif self.ui.new_proxy_mode.currentText() == "Proxy 1/8":
                settings["ProxyWidthHint"] = "0.125"

        return settings

    @property
    def exit_code(self):
        """
        Used to pass exit code back though sgtk dialog

        :returns:    The dialog exit code
        """
        return self.__exit_code

    @property
    def hide_tk_title_bar(self):
        """
        Tell the system to not show the std toolbar
        """
        return True

    def _on_submit_clicked(self):
        """
        Called when the 'submit' button is clicked.
        """
        self.__exit_code = QtGui.QDialog.Accepted
        self.close()

    def _on_abort_clicked(self):
        """
        Called when the 'cancel' button is clicked.
        """
        self.__exit_code = QtGui.QDialog.Rejected
        self.close()

    def _on_help_url_clicked(self):
        """
        Called when someone clicks the help url
        """
        url = self._engine.documentation_url
        if url:
            self._engine.log_debug("Opening documentation url %s..." % url)
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))
        else:
            self._engine.log_warning("No documentation found!")

    def _on_proxy_width_hint_change(self):
        """
        Update slider preview for proxy width hint
        """
        val = self.ui.proxy_width_hint.value()
        self.ui.proxy_width_hint_preview.setText("%s px" % val)
        # min frame size value must be greater or equal to this value
        self.ui.proxy_min_frame_size.setMinimum(val)

    def _on_proxy_min_frame_size_change(self):
        """
        Update slider preview for proxy min size
        """
        val = self.ui.proxy_min_frame_size.value()
        self.ui.proxy_min_frame_size_preview.setText("%d px" % val)

    def _on_proxy_mode_change(self, idx):
        """
        Proxy enabled clicked. Enable/disable a bunch
        of fields based on the value.
        """
        # [off, conditional, on]

        # first turn off everything
        self.ui.proxy_depth.setVisible(False)
        self.ui.proxy_quality.setVisible(False)
        self.ui.proxy_width_hint.setVisible(False)
        self.ui.proxy_width_hint_preview.setVisible(False)
        self.ui.proxy_depth_label.setVisible(False)
        self.ui.proxy_quality_label.setVisible(False)
        self.ui.proxy_width_hint_label.setVisible(False)

        self.ui.proxy_min_frame_size.setVisible(False)
        self.ui.proxy_min_frame_size_preview.setVisible(False)
        self.ui.proxy_above_8_bits.setVisible(False)
        self.ui.proxy_min_frame_size_label.setVisible(False)

        if idx > 0:
            # on / conditional
            self.ui.proxy_depth.setVisible(True)
            self.ui.proxy_quality.setVisible(True)
            self.ui.proxy_width_hint.setVisible(True)
            self.ui.proxy_width_hint_preview.setVisible(True)
            self.ui.proxy_depth_label.setVisible(True)
            self.ui.proxy_quality_label.setVisible(True)
            self.ui.proxy_width_hint_label.setVisible(True)

        if idx == 1:
            # conditional
            self.ui.proxy_min_frame_size.setVisible(True)
            self.ui.proxy_min_frame_size_preview.setVisible(True)
            self.ui.proxy_above_8_bits.setVisible(True)
            self.ui.proxy_min_frame_size_label.setVisible(True)
