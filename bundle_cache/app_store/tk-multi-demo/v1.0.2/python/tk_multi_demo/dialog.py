# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import inspect
import os

import sgtk
from sgtk.platform.qt import QtCore, QtGui
from sgtk.platform import constants

# for reading each demo's demo.yml file
from tank_vendor import yaml

# ensure the resources are available
from .ui import resources_rc

from .demos import DEMO_DEFAULT, DEMOS_LIST

# TODO: file copied from python console.
#       maybe entire python console widget set should live in qtwidgets?
from syntax_highlighter import PythonSyntaxHighlighter

overlay = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "overlay_widget")

# logger for this module
try:
    # core 18
    logger = sgtk.platform.get_logger(__name__)
except:
    # older cores
    import logging
    logger = logging.getLogger(__name__)


def show_dialog(app_instance):
    """
    Shows the main dialog window.

    :param app_instance: The ``sgtk.platform.Application`` instance.
    """
    app_instance.engine.show_dialog(
        "Shotgun Toolkit Demos",
        app_instance,
        DemoWidget
    )


class DemoWidget(QtGui.QSplitter):
    """
    Main application dialog window.
    """

    def __init__(self):
        """
        Initialize the main demo widget.
        """

        self._current_demo_info = None

        super(DemoWidget, self).__init__()

        # easy access to the app instance
        self.app = sgtk.platform.current_bundle()

        # the default class/info to use at startup
        self._default_demo_info = None

        # quick lookup of demo info as selection changes
        self._demo_info_lookup = {}

        # quick lookup of stacked widget positions via demo names
        self._demo_stack_lookup = {}

        # quick lookup of previously created file models via demo names
        self._demo_file_model_lookup = {}

        # keep a reference to all demo widgets created. this will prevent issues
        # with garbage collection
        self.__all_demos = []

        # construct the model based on the hierarchy defined in the
        # demos module
        self._demo_model = self._get_demo_model()

        # build a tree view to show all the demos
        self._demo_tree_view = QtGui.QTreeView()
        self._demo_tree_view.setModel(self._demo_model)
        self._demo_tree_view.setObjectName("demo_tree_view")
        self._demo_tree_view.setIndentation(16)
        self._demo_tree_view.header().hide()
        self._demo_tree_view.expandAll()
        self._demo_tree_view.setRootIsDecorated(False)
        self._demo_tree_view.setFocusPolicy(QtCore.Qt.NoFocus)
        self._demo_tree_view.setMinimumWidth(250)

        # shows the name of the demo
        self._demo_name = QtGui.QLabel(self)
        self._demo_name.setObjectName("demo_name")
        self._demo_name.setMinimumHeight(30)

        # shows the description of the demo
        self._demo_desc = QtGui.QLabel(self)
        self._demo_desc.setObjectName("demo_desc")
        self._demo_desc.setWordWrap(True)
        self._demo_desc.setOpenExternalLinks(True)

        # holds a stack of all demo widgets
        self._demo_widget_tab = QtGui.QStackedWidget()

        # used to display the code associated with the demos
        self._demo_code_edit = QtGui.QPlainTextEdit(self)
        self._demo_code_edit.setObjectName("demo_code_edit")
        self._demo_code_edit.setReadOnly(True)
        self._demo_code_edit.setWordWrapMode(QtGui.QTextOption.NoWrap)

        # a syntax highlighter for the code editor
        self._syntax_highlighter = PythonSyntaxHighlighter(
            self._demo_code_edit.document(),
            self._demo_code_edit.palette()
        )
        self._syntax_highlighter.setDocument(self._demo_code_edit.document())

        # combobox to display all python files in a demo
        self._demo_file_combo = QtGui.QComboBox()
        self._demo_file_combo.setObjectName("demo_file_combo")

        # layout the code tab
        demo_code_layout = QtGui.QVBoxLayout()
        demo_code_layout.addWidget(self._demo_code_edit)
        demo_code_layout.addWidget(self._demo_file_combo)
        demo_code_layout.setAlignment(
            self._demo_file_combo, QtCore.Qt.AlignRight)

        # a single widget to wrap the code layout
        demo_code_widget = QtGui.QWidget()
        demo_code_widget.setLayout(demo_code_layout)

        # tab widget displays the current demo
        self._demo_tabs = QtGui.QTabWidget(self)
        self._demo_tabs.setTabPosition(QtGui.QTabWidget.South)
        self._demo_tabs.setMinimumWidth(625)

        # add the widgets as tabs
        self._demo_tabs.addTab(self._demo_widget_tab, "Interactive Demo")
        self._demo_tabs.addTab(demo_code_widget, "Code")

        # an overlay of the tabs for displaying errors, etc.
        self._overlay = overlay.ShotgunOverlayWidget(self._demo_tabs)

        demo_header_layout = QtGui.QHBoxLayout()
        demo_header_layout.addWidget(self._demo_name)
        demo_header_layout.addStretch()

        # layout the demo display widgets
        demo_layout = QtGui.QVBoxLayout()
        demo_layout.addLayout(demo_header_layout)
        demo_layout.addWidget(self._demo_desc)
        demo_layout.addWidget(self._demo_tabs)

        # wrapper widget for the display layout
        demo_stack = QtGui.QWidget()
        demo_stack.setLayout(demo_layout)

        # add the primary wrapper widgets to this splitter
        self.addWidget(self._demo_tree_view)
        self.addWidget(demo_stack)

        # make the demo side stretch 3x as fast as the demo tree view
        self.setStretchFactor(1, 3)

        # grab the selection model from the tree view and connect it up
        # to handle a new demo being selected
        # NOTE: this has to be done in 2 calls to avoid segfault!
        selection_model = self._demo_tree_view.selectionModel()
        selection_model.selectionChanged.connect(
            self._on_selection_changed
        )

        # handle the user selecting a new file to display in the code widget
        self._demo_file_combo.activated[str].connect(self._on_file_selected)

        # set the default demo
        self._set_default_demo()

        QtCore.QCoreApplication.instance().aboutToQuit.connect(self.destroy)

    def destroy(self):
        """Manually call destroy on the created demos.

        This allows them to do their own cleanup.
        """

        for demo in self.__all_demos:
            demo.destroy()

    def set_demo(self, demo_info):
        """
        Given a dict of info about a demo, show it in the UI.

        :param dict demo_info: A dict of info about the demo to display

        The ``demo_info`` holds the information parsed from the demo's
        ``demo.yml`` file. It has one additional field called ``widget_class``
        which stores the class for the demo widget itself.
        """

        self._current_demo_info = demo_info

        # grab the necessary info about the demo to display
        demo_name = demo_info["display_name"]
        demo_desc = demo_info["description"]
        demo_doc_url = demo_info["documentation_url"]
        demo_class = demo_info["widget_class"]

        # set the name label
        name_color = self.palette().highlight().color().name()
        self._demo_name.setText(
            "<h2><font color='%s'>%s</font></h2>" %
            (name_color, demo_name)
        )

        # show the description label
        demo_desc += (
            "&nbsp;&nbsp;<a href='%s'>Click for full docs...</a>"
            % (demo_doc_url,)
        )
        self._demo_desc.setText(demo_desc)

        # get an instance of the widget and add it to the stack. if an instance
        # of the class hasn't been created, try to create it and add it to the
        # demo stack lookup
        if demo_name not in self._demo_stack_lookup:
            try:
                widget = demo_class(parent=self)
                demo_dir = os.path.dirname(inspect.getfile(demo_class))
                self._apply_external_styleshet(widget, demo_dir)
            except Exception, e:
                import traceback
                tb = traceback.format_exc()
                self._overlay.show_error_message(
                    "Uh oh! Unable to load the demo! Here's the error: "
                    "\n\n%s\n%s" % (e, tb)
                )
                return

            # keep a reference to all created widgets to avoid problems with
            # garbage collection
            self.__all_demos.append(widget)

            stack_pos = self._demo_widget_tab.addWidget(widget)
            self._demo_stack_lookup[demo_name] = stack_pos

        # ensure any previous overlay is hidden
        self._overlay.hide()

        # set the stacked widget index based on the name of the demo to display
        self._demo_widget_tab.setCurrentIndex(
            self._demo_stack_lookup[demo_name])

        # if this demo hasn't previously been shown, create a data model of all
        # the python files in the demo directory
        if demo_name not in self._demo_file_model_lookup:
            file_model = self._get_file_model(demo_class)
            self._demo_file_model_lookup[demo_name] = file_model

        # show the file model as a list in the combo box
        file_model = self._demo_file_model_lookup[demo_name]
        self._demo_file_combo.setModel(file_model)

        # try to find a demo.py file in the model and use that
        index = self._demo_file_combo.findText("demo.py")
        if index != -1:
            self._demo_file_combo.setCurrentIndex(index)
            self._on_file_selected(self._demo_file_combo.currentText())

    def _get_file_model(self, demo_class):
        """
        Returns a file model for all python files in the class directory.

        :param demo_class: The widget class for a demo.

        :returns: A ``QtGui.QStandardItemModel``
        """

        # the parent directory of the supplied class
        demo_dir = os.path.dirname(inspect.getfile(demo_class))

        # create a model to populate
        model = QtGui.QStandardItemModel()
        parent = model.invisibleRootItem()

        # walk the directory and construct file paths
        for (root, dirs, files) in os.walk(demo_dir):
            for file_path in files:

                # we only display the python files for now
                if file_path.endswith(".py") or file_path.endswith(".qss"):

                    # display a path relative to the demo directory
                    display = os.path.join(root[len(demo_dir)+1:], file_path)

                    # create the item for display
                    item = QtGui.QStandardItem(display)
                    item.setIcon(QtGui.QIcon(":/tk_multi_demo/file.png"))

                    # remember the full path for later retrieval
                    item.setData(os.path.join(root, file_path))

                    # add the item to the model
                    parent.appendRow(item)

        return model

    def _on_file_selected(self, file_name):
        """
        Handle selection of a python file in the code combo.

        :param file_name: The display name of a file in the combo
        :return:
        """

        # get the model
        model = self._demo_file_combo.model()

        # locate the corresponding item
        items = model.findItems(file_name)
        if not items:
            return
        item = items[0]

        # extract the full path to the file
        full_path = item.data()

        # open an display the contents in the edit widget
        fh = open(full_path)
        try:
            python_script = "".join(fh.readlines())
            self._demo_code_edit.setPlainText(python_script)
        finally:
            fh.close()

    def _on_selection_changed(self, selected, deselected):
        """
        Handle selection changes in the demo list

        :param selected: ``QtGui.QItemSelection`` representing new selections
        :param deselected: ``QtGui.QItemSelection`` representing items that were
            deselected
        """

        # if nothing selected, show the default demo
        if not selected.indexes():
            self._set_default_demo()
        else:
            # get the selection and set the appropriate demo
            index = selected.indexes()[0]
            item = self._demo_tree_view.model().itemFromIndex(index)
            if item.text() in self._demo_info_lookup:
                self.set_demo(self._demo_info_lookup[item.text()])
            else:
                # couldn't find the demo, just show the default
                self._set_default_demo()

    def _get_demo_model(self):
        """
        Constructs a model of all available demos as defined by ``DEMO_LIST``.

        :returns: A ``QtGui.QStandardItemModel``
        """

        # construct the model
        model = QtGui.QStandardItemModel()
        parent = model.invisibleRootItem()

        # this is just a list of group names and demo classes to build a
        # model from. the strings represent the headers/parents in the model.
        # each time one is encountered, parent subsequent demo class items
        # underneath it in the model
        for d in DEMOS_LIST:

            # a group of demos to display in the UI
            if isinstance(d, basestring):

                # create the item
                group_item = QtGui.QStandardItem(d)
                group_item.setEditable(False)
                group_item.setSelectable(False)

                # display it a little differently to distinguish
                group_item.setForeground(
                    self.palette().light().color()
                )
                model.invisibleRootItem().appendRow(group_item)

                # this is now the parent for subsequent demo class items
                parent = group_item

            # this is a demo class
            elif issubclass(d, QtGui.QWidget):

                # get the info for the class to add to the lookup
                demo_class = d
                demo_info = self._get_demo_info(demo_class)

                # oops, likely no `demo.yml` for this demo
                if not demo_info:
                    continue

                # keep note of this info if this is the default demo
                if demo_class == DEMO_DEFAULT:
                    self._default_demo_info = demo_info

                # add to the lookup
                display_name = demo_info["display_name"]
                self._demo_info_lookup[display_name] = demo_info

                # create the item and parent it under the current group
                demo_item = QtGui.QStandardItem(display_name)
                demo_item.setEditable(False)
                parent.appendRow(demo_item)

        # never did find a default, just use the first one alphabetically.
        # there's probably a better UX here, but this shouldn't ever happen.
        if not self._default_demo_info:
            demo_names = sorted(self._demo_info_lookup.keys())
            self._default_demo_info = self._demo_info_lookup[demo_names[0]]

        return model

    def _get_demo_info(self, demo_class):
        """
        Given a demo class, parse the ``demo.yml`` file for more info.

        :param demo_class: The demo ``QtGui.QWidget`` subclass

        :returns: A dict of info about the demo class.
        """

        # read the demo.yml file from the demo_class's directory
        demo_dir = os.path.dirname(inspect.getfile(demo_class))

        # construct the full path to the manifest
        manifest = os.path.join(demo_dir, "demo.yml")

        if not os.path.exists:
            # no path fo the manifest
            logger.error(
                "No manifest file exists for this demo class: %s." %
                (demo_class,)
            )
            return None

        # attempt to read the manifest file
        try:
            fh = open(manifest, "r")
        except Exception, e:
            logger.error(
                "Could not open demo manifest file '%s'.\n"
                " Error reported: '%s'" % (manifest, e)
            )
            return None

        # now try to parse it
        try:
            demo_info = yaml.load(fh)
        except Exception, e:
            logger.error(
                "Could not parse demo manifest file '%s'.\n"
                " Error reported: '%s'" % (manifest, e)
            )
            return None
        finally:
            fh.close()

        # make sure the required fields are present
        for field in ["display_name", "description", "documentation_url"]:
            if field not in demo_info:
                logger.error(
                    "The `%s` field is missing from the demo "
                    "manifest file: %s." % (field, manifest)
                )
                return None

        # add the directory and class in there as well so that we have one stop
        # shopping for all the demo information
        demo_info["widget_class"] = demo_class
        demo_info["directory"] = demo_dir

        return demo_info

    def _set_default_demo(self):
        """
        Displays the default demo.
        """
        self.set_demo(self._default_demo_info)

    def _apply_external_styleshet(self, widget, demo_dir):
        """
        Apply an std external stylesheet, associated with the demo.

        :param bundle: app/engine/framework instance to load style sheet from
        :param widget: widget to apply stylesheet to
        """
        qss_file = os.path.join(demo_dir, constants.BUNDLE_STYLESHEET_FILE)
        try:
            f = open(qss_file, "rt")
            try:
                # Read css file
                self.app.log_debug(
                    "Detected std style sheet file '%s' - applying to widget %s"
                    % (qss_file, widget)
                )
                qss_data = f.read()
                # resolve tokens
                qss_data = self._resolve_sg_stylesheet_tokens(qss_data)
                # apply to widget (and all its children)
                widget.setStyleSheet(qss_data)
            except Exception, e:
                # catch-all and issue a warning and continue.
                self.app.log_warning(
                    "Could not apply stylesheet '%s': %s" % (qss_file, e))
            finally:
                f.close()
        except IOError:
            # The file didn't exist, so nothing to do.
            pass

    def _resolve_sg_stylesheet_tokens(self, style_sheet):
        """
        Given a string containing a qt style sheet,
        perform replacements of key toolkit tokens.

        For example, "{{SG_HIGHLIGHT_COLOR}}" is converted to "#30A7E3"

        :param style_sheet: Stylesheet string to process
        :returns: Stylesheet string with replacements applied
        """
        processed_style_sheet = style_sheet
        for (token, value) in constants.SG_STYLESHEET_CONSTANTS.iteritems():
            processed_style_sheet = processed_style_sheet.replace(
                "{{%s}}" % token, value)
        return processed_style_sheet
