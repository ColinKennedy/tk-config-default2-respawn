# Copyright (c) 2015 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Alembic Output node App for use with Toolkit's Houdini engine.
"""

import sgtk


class TkAlembicNodeApp(sgtk.platform.Application):
    """The Alembic Output Node."""

    def init_app(self):
        """Initialize the app."""

        tk_houdini_alembic = self.import_module("tk_houdini_alembicnode")
        self.handler = tk_houdini_alembic.TkAlembicNodeHandler(self)

    def convert_to_regular_alembic_nodes(self):
        """Convert Toolkit Alembic nodes to regular Alembic nodes.
        
        Convert all Toolkit Alembic nodes found in the current script to
        regular Alembic nodes. Additional Toolkit information will be stored in
        user data named 'tk_*'

        Example usage::

        >>> import sgtk
        >>> eng = sgtk.platform.current_engine()
        >>> app = eng.apps["tk-houdini-alembicnode"]
        >>> app.convert_to_regular_alembic_nodes()

        """

        self.log_debug(
            "Converting Toolkit Alembic nodes to built-in Alembic nodes.")
        tk_houdini_alembic = self.import_module("tk_houdini_alembicnode")
        tk_houdini_alembic.TkAlembicNodeHandler.\
            convert_to_regular_alembic_nodes(self)

    def convert_back_to_tk_alembic_nodes(self):
        """Convert regular Alembic nodes back to Tooklit Alembic nodes.
        
        Convert any regular Alembic nodes that were previously converted
        from Tooklit Alembic nodes back into Toolkit Alembic nodes.

        Example usage::

        >>> import sgtk
        >>> eng = sgtk.platform.current_engine()
        >>> app = eng.apps["tk-houdini-alembicnode"]
        >>> app.convert_back_to_tk_alembic_nodes()

        """

        self.log_debug(
            "Converting built-in Alembic nodes back to Toolkit Alembic nodes.")
        tk_houdini_alembic = self.import_module("tk_houdini_alembicnode")
        tk_houdini_alembic.TkAlembicNodeHandler.\
            convert_back_to_tk_alembic_nodes(self)

    def get_nodes(self):
        """
        Returns a list of hou.node objects for each tk alembic node.

        Example usage::

        >>> import sgtk
        >>> eng = sgtk.platform.current_engine()
        >>> app = eng.apps["tk-houdini-alembicnode"]
        >>> tk_alembic_nodes = app.get_nodes()
        """

        self.log_debug("Retrieving tk-houdini-alembic nodes...")
        tk_houdini_alembic = self.import_module("tk_houdini_alembicnode")
        nodes = tk_houdini_alembic.TkAlembicNodeHandler.\
            get_all_tk_alembic_nodes()
        self.log_debug("Found %s tk-houdini-alembic nodes." % (len(nodes),))
        return nodes

    def get_output_path(self, node):
        """
        Returns the evaluated output path for the supplied node.

        Example usage::

        >>> import sgtk
        >>> eng = sgtk.platform.current_engine()
        >>> app = eng.apps["tk-houdini-alembicnode"]
        >>> output_path = app.get_output_path(tk_alembic_node)
        """

        self.log_debug("Retrieving output path for %s" % (node,))
        tk_houdini_alembic = self.import_module("tk_houdini_alembicnode")
        output_path = tk_houdini_alembic.TkAlembicNodeHandler.\
            get_output_path(node)
        self.log_debug("Retrieved output path: %s" % (output_path,))
        return output_path

    def get_work_file_template(self):
        """
        Returns the configured work file template for the app.
        """

        return self.get_template("work_file_template")
