# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()

class HieroPostVersionCreation(HookBaseClass):
	"""
	This class implements a hook that can be used to add custom logic to
	be run after a Version entity is created in Shotgun as part of the
	export process.
	"""
	def execute(self, version_data, **kwargs):
		"""
		Runs following the creation of the Version entity in Shotgun. The
		provided version data is the data structure containing information
		about the Version entity, including its ID in Shotgun.

		Example version_data:

		.. code-block:: python

			{'code': 'Scene_v031_abc',
			 'created_by': {'id': 39, 'name': 'Jeff Beeland', 'type': 'HumanUser'},
			 'entity': {'id': 1166, 'name': 'ABC', 'type': 'Shot'},
			 'id': 6039,
			 'project': {'id': 74, 'name': 'DevWindows', 'type': 'Project'},
			 'published_files': [{'id': 108,
			                      'name': 'scene_v031_ABC.mov',
			                      'type': 'PublishedFile'}],
			 'sg_path_to_movie': '/shotgun/projects/devwindows/sequences/123/ABC/editorial/2015_11_24/plates/scene_v031_ABC.mov',
			 'sg_task': {'id': 2113, 'name': 'Comp', 'type': 'Task'},
			 'type': 'Version',
			 'user': {'id': 39, 'name': 'Jeff Beeland', 'type': 'HumanUser'}}

		:param dict version_data: The Version entity that was created in Shotgun.
		"""
		pass
