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

# import the overlay module from the qtwidgets framework
overlay = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "overlay_widget")

# import the shotgun fields module from qtwidgets.
shotgun_fields = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "shotgun_fields")

# import the views module from qtwidgets framework
views = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "views")

# import the shotgun model module from shotgunutils framework
shotgun_model = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_model")

# import the task manager from shotgunutils framework
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager")


class ShotgunHierarchyDemo(QtGui.QWidget):
    """
    Demonstrates the use of the ``ShotgunHierarchyModel`` to display a hierarchy
    as defined by project's tracking settings in Shotgun.
    """

    def __init__(self, parent=None):
        """
        Return the ``QtGui.QWidget`` instance for this demo.
        """

        super(ShotgunHierarchyDemo, self).__init__(parent)

        # create a background task manager for each of our components to use
        # for threading
        self._bg_task_manager = task_manager.BackgroundTaskManager(self)

        doc_lbl = QtGui.QLabel(
            "Browse the hierarchy on the left to find <tt>Version</tt> "
            "entities."
        )

        # the field manager handles retrieving widgets for shotgun field types
        self._fields_manager = shotgun_fields.ShotgunFieldManager(
            self, bg_task_manager=self._bg_task_manager)

        # construct the view and set the model
        self._hierarchy_view = QtGui.QTreeView()
        self._hierarchy_view.setIndentation(16)
        self._hierarchy_view.setUniformRowHeights(True)
        self._hierarchy_view.setSortingEnabled(True)
        self._hierarchy_view.sortByColumn(0, QtCore.Qt.AscendingOrder)

        # this view will display versions for selected entites on the left
        self._version_view = views.ShotgunTableView(self._fields_manager)
        self._version_view.horizontalHeader().setStretchLastSection(True)

        # add an overlay to the version view to show messages while querying
        self._overlay_widget = overlay.ShotgunOverlayWidget(self._version_view)

        # layout the widgets for display
        splitter = QtGui.QSplitter()
        splitter.addWidget(self._hierarchy_view)
        splitter.addWidget(self._version_view)

        # version view stretch twice the rate of hierarchy
        splitter.setStretchFactor(1, 2)

        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(doc_lbl)
        layout.addWidget(splitter)

        # splitter should dominate vertically
        layout.setStretchFactor(splitter, 10)

        # the fields manager needs time to initialize itself. once that's done,
        # the widgets can begin to be populated.
        self._fields_manager.initialized.connect(self._populate_ui)
        self._fields_manager.initialize()

    def destroy(self):
        """
        Destroy the model as required by the API.
        """
        try:
            self._hierarchy_model.destroy()
            self._bg_task_manager.shut_down()
        except Exception, e:
            # log exception
            pass

    def _populate_ui(self):
        """
        Populate the UI with the data.
        """

        # construct a hierarchy model then load some data.
        # "Version.entity" seed means build a hierarchy that leads to
        # entities that are linked via the Version.entity field.
        # by default the model will be built for the current project.
        # if no project can be determined from the current context,
        # the model will be built with top-level items for each project.
        self._hierarchy_model = shotgun_model.SimpleShotgunHierarchyModel(
            self, bg_task_manager=self._bg_task_manager)
        self._hierarchy_model.load_data("Version.entity")

        # create a proxy model to sort the hierarchy
        self._hierarchy_proxy_model = QtGui.QSortFilterProxyModel(self)
        self._hierarchy_proxy_model.setDynamicSortFilter(True)

        # set the proxy model's source to the hierarchy model
        self._hierarchy_proxy_model.setSourceModel(self._hierarchy_model)

        # set the proxy model as the data source for the view
        self._hierarchy_view.setModel(self._hierarchy_proxy_model)

        # create a simple shotgun model for querying the versions
        self._version_model = shotgun_model.SimpleShotgunModel(
            self, bg_task_manager=self._bg_task_manager)

        # --- connect some signals

        # as hierarchy view selection changes, query versions
        selection_model = self._hierarchy_view.selectionModel()
        selection_model.selectionChanged.connect(
            self._on_hierarchy_selection_changed
        )

        # show the overlay on the versions as they're being queried
        self._version_model.data_refreshing.connect(
            lambda: self._overlay_widget.start_spin()
        )
        self._version_model.data_refreshed.connect(self._on_data_refreshed)

    def _on_hierarchy_selection_changed(self, selected, deselected):
        """
        Handles selection changes in the hierarchy view.
        """

        # for this demo, we only care about the first item selected
        indexes = selected.indexes()
        if not indexes:
            return

        # get the item from the source model
        selected_item = self._hierarchy_model.itemFromIndex(
            # get the source hierarchy model index
            self._hierarchy_proxy_model.mapToSource(indexes[0])
        )

        # the item will be a ShotgunHierarchyItem. Access the data necessary
        # to load data for the shotgun model
        try:
            target_entities = selected_item.target_entities()
        except AttributeError, e:
            # item doesn't have target entities
            return

        if not target_entities:
            self._overlay_widget.show_message("No Versions under selection.")
            return

        # if we're here we have a hierarchy item. query the versions under
        # the selected point in the SG hierarchy. the shotgun model will handle
        # caching as the user clicks a previously selected item in the hierarchy
        self._version_model.load_data(
            target_entities.get("type"),
            additional_filter_presets=target_entities.get("additional_filter_presets"),
            limit=50,           # limit results to 50 Versions max
            columns=[           # a few columns to display in the model
                "created_at",
                "created_by",
                "sg_task",
            ],
        )

        # delay setting the view model until the first query
        if not self._version_view.model():
            self._version_view.setModel(self._version_model)

    def _on_data_refreshed(self):
        """
        Update the display when the data has been refreshed.
        """
        self._overlay_widget.hide()

        # if the row count of the model is 0, there are no versions to show.
        # show a message instead
        if self._version_model.rowCount() == 0:
            self._overlay_widget.show_message("No Versions under selection.")
        else:
            self._version_view.resizeColumnsToContents()

