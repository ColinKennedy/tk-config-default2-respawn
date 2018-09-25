# Copyright (c) 2016 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk
from sgtk.platform.qt import QtCore, QtGui

# import the context_selector module from the qtwidgets framework
context_selector = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "context_selector")

# import the task_manager module from shotgunutils framework
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager")

# import the shotgun_globals module from shotgunutils framework
shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals")

logger = sgtk.platform.get_logger(__name__)


class ContextWidgetDemo(QtGui.QWidget):
    """
    Demonstrates the use of the the ContextSelector class available in the
    tk-frameworks-qtwidgets framework.
    """

    def __init__(self, parent=None):
        """
        Initialize the widget instance.
        """

        # call the base class init
        super(ContextWidgetDemo, self).__init__(parent)

        # create a background task manager for each of our components to use
        self._task_manager = task_manager.BackgroundTaskManager(self)

        self._context_widget = context_selector.ContextWidget(self)
        self._context_widget.set_up(self._task_manager)
        self._context_widget.setFixedWidth(400)

        # Specify what entries should show up in the list of links when using
        # the auto completer. In this case, we only show entity types that are
        # allowed for the PublishedFile.entity field. You can provide an
        # explicit list with the `restrict_entity_types()` method.
        self._context_widget.restrict_entity_types_by_link(
            "PublishedFile", "entity")

        # You can set the tooltip for each sub widget for context selection.
        # This helps describe to the user why they're choosing a task or link.
        self._context_widget.set_task_tooltip(
            "<p>The task that the selected item will be associated with "
            "the Shotgun entity being acted upon.</p>"
        )
        self._context_widget.set_link_tooltip(
            "<p>The link that the selected item will be associated with "
            "the Shotgun entity being acted upon.</p>"
        )

        # connect the signal emitted by the selector widget when a context is
        # selected. The connected callable should accept a context object.
        self._context_widget.context_changed.connect(
            self._on_item_context_change)

        # just a label to display the selected context as text
        self._context_lbl = QtGui.QLabel()

        # a button to toggle editing. the widget's editing capabilities can be
        # turned on/off. you can set the text to display in either state by
        # supplying it as an argument to the `enable_editing` method on the
        # widget. See the connected callable (self._enable_editing) for an
        # example.
        self._enable_editing(True)
        _enable_editing_btn = QtGui.QPushButton("Click to Toggle Editing")
        _enable_editing_btn.setCheckable(True)
        _enable_editing_btn.setChecked(True)
        _enable_editing_btn.setFixedWidth(150)
        _enable_editing_btn.toggled.connect(self._enable_editing)

        # lay out the widgets
        layout = QtGui.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignHCenter)
        layout.addStretch()
        layout.addWidget(self._context_widget)
        layout.addSpacing(12)
        layout.addWidget(_enable_editing_btn)
        layout.addWidget(self._context_lbl)
        layout.addStretch()

        # you can set a context using the `set_context()` method. Here we set it
        # to the current bundle's context
        self._context_widget.set_context(sgtk.platform.current_bundle().context)

    def closeEvent(self, event):
        """
        Executed when the main dialog is closed.
        All worker threads and other things which need a proper shutdown
        need to be called here.
        """

        logger.debug("CloseEvent Received. Begin shutting down UI.")

        # register the data fetcher with the global schema manager
        shotgun_globals.unregister_bg_task_manager(self._task_manager)

        try:
            # shut down main threadpool
            self._task_manager.shut_down()
        except Exception:
            logger.exception("Error running closeEvent()")

        # ensure the context widget's recent contexts are saved
        self._context_widget.save_recent_contexts()

    def _on_item_context_change(self, context):
        """
        This method is connected above to the `context_changed` signal emitted
        by the context selector widget.

        For demo purposes, we simply display the context in a label.
        """
        self._context_lbl.setText("Context set to: %s" % (context,))

        # typically the context would be set by some external process. for now,
        # we'll just re-set the context based on what was selected. this will
        # have the added effect of populating the "recent" items in the drop
        # down list
        self._context_widget.set_context(context)

    def _enable_editing(self, checked):
        """
        This method is connected above to the toggle button to show switching
        between enabling and disabling editing of the context.
        """

        self._context_lbl.setText("")

        if checked:
            # enable editing and show a message to the user
            self._context_widget.enable_editing(
                True,
                "Editing is now enabled."
            )
        else:
            # disable editing and show a message to the user
            self._context_widget.enable_editing(
                False,
                "Editing is now disabled."
            )
