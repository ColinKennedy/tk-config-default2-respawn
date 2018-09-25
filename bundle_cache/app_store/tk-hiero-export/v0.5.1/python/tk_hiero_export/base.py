# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sys
import shutil
import time
import collections

import hiero.core
from hiero.exporters import FnShotExporter
from hiero.exporters import FnShotProcessor
from hiero.exporters import FnTranscodeExporter
from hiero.ui.FnUIProperty import UIPropertyFactory

import tank
from tank.platform.qt import QtGui, QtCore

from . import HieroCustomizeExportUI


class ShotgunHieroObjectBase(object):
    """Base class to make the Hiero classes app aware."""
    _app = None

    @classmethod
    def setApp(cls, app):
        cls._app = app

    @property
    def app(self):
        return self._app

    def _get_custom_properties(self, get_method):
        """
        Gets a list of custom property descriptions from the customize_export_ui
        hook, calling the hook method provided. This method will cache the
        list of property descriptions, and any subsequent calls here will
        return cached data.

        :param str get_method: The name of the getter hook method to call.

        :returns: A list of property definition dictionaries, as returned by
            the hook_customize_export_ui hook getter methods.
        :rtype: list
        """
        # This base class isn't intended to be run through an __init__ since
        # it's a utility container used as part of a mixin. Little backwards
        # here, but if we don't have a cache location for these property
        # definitions we can just create it here before moving on.
        if not hasattr(self, "_custom_property_definitions"):
            self._custom_property_definitions = dict()

        # We key off of the method name since we allow for different
        # properties and custom widgets per exporter type.
        if get_method not in self._custom_property_definitions:
            self._custom_property_definitions[get_method] = self.app.execute_hook_method(
                "hook_customize_export_ui",
                get_method,
                base_class=HieroCustomizeExportUI,
            )

        return self._custom_property_definitions[get_method]

    def _get_custom_widget(self, parent, create_method, get_method, set_method, properties=None):
        """
        Uses the customize_export_ui hook to get a custom widget, get custom
        property definitions, and then set the widget's settings.

        :param parent: The parent widget.
        :param str create_method: The name of the create widget hook method to
            call to get the custom widget.
        :param str get_method: The name of the property getter hook method to
            call to get the custom property definitions.
        :param str set_method: The name of the widget property setter hook method
            to call to setup the widget using the custom properties.
        :param dict properties: The processor's properties dictionary to
            associate with any custom UIProperty objects created.

        :returns: A widget, or None if no custom widget was provided by the
            hook.
        """
        properties = properties or self._preset.properties()
        hook_name = "hook_customize_export_ui"
        hook_widget = self.app.execute_hook_method(
            hook_name,
            create_method,
            parent_widget=parent,
            base_class=HieroCustomizeExportUI,
        )

        if hook_widget is not None:
            hook_ui_properties = self._get_custom_properties(get_method)

            # This base class isn't intended to be run through an __init__ since
            # it's utility container class used as part of a mixin. Little backwards
            # here, but if we don't have a cache location for these properties
            # we can just create it here before moving on.
            if not hasattr(self, "_custom_properties"):
                self._custom_properties = dict()

            # We're only adding these property objects to a property in order
            # to protect them from garbage collections. We'll key it off of the
            # hook get method name since you'll end up with different property
            # objects per exporter type.
            #
            # Caching using an OrderedDict because we want to maintain the property
            # order as defined in the hook's get properties method. This means that
            # the programmer can define the properties in the order that they want
            # them to appear in a Qt layout and just iterate over what we give them
            # in the set properties hook method. NOTE: OrderedDict is Python 2.7+,
            # but that's safe here because we only support Hiero/NS versions that
            # come bundled with 2.7.
            cache = self._custom_properties.setdefault(
                get_method,
                collections.OrderedDict(),
            )

            for prop_data in hook_ui_properties:
                cache[prop_data["label"]] = UIPropertyFactory.create(
                    type(prop_data["value"]),
                    key=prop_data["name"],
                    value=prop_data["value"],
                    dictionary=properties,
                    tooltip=prop_data["tooltip"],
                )

            self.app.execute_hook_method(
                hook_name,
                set_method,
                widget=hook_widget,
                properties=self._custom_properties[get_method],
                base_class=HieroCustomizeExportUI,
            )

        return hook_widget

    def _formatTkVersionString(self, hiero_version_str):
        """Reformat the Hiero version string to the tk format.
        """
        try:
            version_number = int(hiero_version_str[1:])
        except ValueError:
            # Version is sometimes a glob expression (when building tracks for example)
            # in these cases, return the original string without the leading 'v'
            return hiero_version_str[1:]

        version_template = self.app.get_template('template_version')
        tk_version_str = version_template.apply_fields({'version': version_number})
        return tk_version_str

    def _upload_thumbnail_to_sg(self, sg_entity, thumb_qimage):
        """
        Updates the thumbnail for an entity in Shotgun
        """
        import tempfile
        import uuid

        thumbdir = tempfile.mkdtemp(prefix='hiero_process_thumbnail_')
        try:
            path = "%s.png" % os.path.join(thumbdir, sg_entity.get('name', 'thumbnail'))
            # scale it down to 600px wide
            thumb_qimage_scaled = thumb_qimage.scaledToWidth(600, QtCore.Qt.SmoothTransformation)
            thumb_qimage_scaled.save(path)
            self.app.log_debug("Uploading thumbnail for %s %s..." % (sg_entity['type'], sg_entity['id']))
            self.app.shotgun.upload_thumbnail(sg_entity['type'], sg_entity['id'], path)
        except Exception, e:
            self.app.log_info("Thumbnail for %s %s (#%s) was not refreshed in Shotgun: %s" % (sg_entity['type'], sg_entity.get('name'), sg_entity['id'], e))
        finally:
            # Sometimes Windows holds on to the temporary thumbnail file longer than expected which
            # can cause an exception here. If we wait a second and try again, this usually solves
            # the issue.
            try:
                shutil.rmtree(thumbdir)
            except Exception:
                self.parent.log_error("Error removing temporary thumbnail file, trying again.")
                time.sleep(1.0)
                shutil.rmtree(thumbdir)

    def _cutsSupported(self):
        """Returns True if the site has Cut support, False otherwise."""
        return self.app.shotgun.server_caps.version >= (7, 0, 0)




