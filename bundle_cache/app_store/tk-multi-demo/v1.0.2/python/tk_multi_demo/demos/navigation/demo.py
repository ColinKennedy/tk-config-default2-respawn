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

from .ui.nav_widget_demo import Ui_NavigationWidgetDemoUI

# import the navigation module from the qtwidgets framework
navigation = sgtk.platform.import_framework(
    "tk-framework-qtwidgets", "navigation")

# import the shotgun_model module from the shotgunutils framework
shotgun_model = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_model")

# import the task manager from shotgunutils framework
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager")

class NavigationDemo(QtGui.QWidget):
    """
    Demonstrates the use of the the navigation classes available in the
    tk-frameworks-qtwidgets framework.
    """

    def __init__(self, parent=None):
        """
        Initialize the demo widget.
        """

        # call the base class init
        super(NavigationDemo, self).__init__(parent)

        # get a handle on the current toolkit bundle (the demo app).
        self._app = sgtk.platform.current_bundle()

        # create a background task manager for the widget to use
        self._bg_task_manager = task_manager.BackgroundTaskManager(self)

        # keep track of when we're navigating
        self._navigating = False

        # setup the designer UI
        self.ui = Ui_NavigationWidgetDemoUI()
        self.ui.setupUi(self)

        project = self._app.get_demo_entity("Project")
        if not project:
            raise Exception("Could not find suitable project for this demo!")

        # create a hierarchy model to display data an attach it to the view
        self._hierarchy_model = shotgun_model.SimpleShotgunHierarchyModel(self)

        # create a proxy model to sort the hierarchy
        self._hierarchy_proxy_model = QtGui.QSortFilterProxyModel(self)
        self._hierarchy_proxy_model.setDynamicSortFilter(True)

        # set the proxy model's source to the hierarchy model
        self._hierarchy_proxy_model.setSourceModel(self._hierarchy_model)

        # set the proxy model as the data source for the view
        self.ui.tree_view.setModel(self._hierarchy_proxy_model)
        self.ui.tree_view.header().hide()
        self.ui.tree_view.setSortingEnabled(True)
        self.ui.tree_view.sortByColumn(0, QtCore.Qt.AscendingOrder)

        # build a hierarchy for the current project targeting entities linked
        # to the "entity" field on "Version" entities
        self._hierarchy_model.load_data("Version.entity")

        # ---- connect some signals

        # handle navigation widget clicks
        self.ui.nav_widget.home_clicked.connect(self._on_home_clicked)
        self.ui.nav_widget.navigate.connect(self._on_navigate)

        # now handle hierarchy selection
        selection_model = self.ui.tree_view.selectionModel()
        selection_model.selectionChanged.connect(
            self._on_hierarchy_selection_changed
        )

    def destroy(self):
        """Clean up the object when deleted."""
        self._bg_task_manager.shut_down()

    def _on_hierarchy_selection_changed(self, selected, deselected):
        """As an item in the hierarchy is selected, update the nav widgets."""

        # for this demo, we only care about the first item selected
        indexes = selected.indexes()
        if not indexes:
            return

        # get the item from the source model
        selected_item = self._hierarchy_model.itemFromIndex(
            # get the source hierarchy model index
            self._hierarchy_proxy_model.mapToSource(indexes[0])
        )

        # get a label to display this item in the nav history
        label = _get_item_label(selected_item)

        if not self._navigating:
            # this selection change was not triggered by nav widget click.
            # so it is ok to add the selected item to the nav history

            # add this item to the navigation history
            self.ui.nav_widget.add_destination(label, selected_item)

        # keep a breadcrumb list of the item hierarchy
        crumbs = [_HierarchyItemBreadcrumb(selected_item)]

        # get all the item's parents
        cur_item = selected_item
        while cur_item.parent() is not None:
            parent = cur_item.parent()
            crumbs.insert(0, _HierarchyItemBreadcrumb(parent))
            cur_item = parent

        self.ui.breadcrumb_widget.set(crumbs)

    def _on_navigate(self, item):
        """User navigated to a prev/next destination."""

        # select the item in the tree
        self._navigating = True
        proxy_index = self._hierarchy_proxy_model.mapFromSource(item.index())
        self.ui.tree_view.selectionModel().select(proxy_index,
            QtGui.QItemSelectionModel.ClearAndSelect)
        self._navigating = False

    def _on_home_clicked(self):
        """Go home. For this demo, just clear selection."""

        # clear the tree selection
        self.ui.tree_view.selectionModel().clearSelection()

        # clear the breadcrumbs
        self.ui.breadcrumb_widget.set([])

class _HierarchyItemBreadcrumb(navigation.Breadcrumb):
    """A breadcrumb that holds a hierarchy item."""

    def __init__(self, item):
        """Initialize the breadcrumb."""

        self._item = item

        label = _get_item_label(item)

        # call the base class and supply a label
        super(_HierarchyItemBreadcrumb, self).__init__(label)

    def item(self):
        """The item this breadcrumb represents."""
        return self._item


def _get_item_label(item):
    """Get a display label for a shotgun hierarchy item."""

    if item.kind() == "entity":
        label = "<strong>%s</strong> %s" % (item.entity_type(), item.text())
    else:
        label = item.text()

    return label
