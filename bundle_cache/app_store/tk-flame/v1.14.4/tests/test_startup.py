# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from __future__ import with_statement
import os
import sys

from tank_test.tank_test_base import TankTestBase
from tank_test.tank_test_base import setUpModule # noqa

import sgtk

import mock
import contextlib


repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
print "tk-flame repository root found at %s." % repo_root


class TestStartup(TankTestBase):
    """
    Tests the startup logic for Flame.
    """
    FLAME_2018_PATH = "/opt/Autodesk/flame_2018/bin/startApplication"
    FLAME_2018_INSTALL_ROOT = "/opt/Autodesk"
    FLAME_2018_PYTHON = "/opt/Autodesk/python/2018/bin/python"

    def setUp(self):
        """
        Prepares the environment for unit tests.
        """
        super(TestStartup, self).setUp()

        # Add an environment variable that will allow the Toolkit environment to pick up the
        # engine's code.
        patch = mock.patch.dict("os.environ", {"TK_FLAME_REPO_ROOT": repo_root})
        self.addCleanup(patch.stop)
        patch.start()

        # Setup the fixture. This will take the configuration at fixtures/config inside this
        # repo.
        self.setup_fixtures()

    def _get_classic_environment_2018(self):
        """
        Returns the expected environment variables dictionary for a Toolkit classic launch.
        """
        expected = dict(
            TOOLKIT_CONTEXT=sgtk.context.create_empty(self.tk).serialize(),
            TOOLKIT_ENGINE_NAME="tk-flame",
            TOOLKIT_FLAME_INSTALL_ROOT=self.FLAME_2018_INSTALL_ROOT,
            TOOLKIT_FLAME_VERSION="2018",
            TOOLKIT_FLAME_MAJOR_VERSION="2018",
            TOOLKIT_FLAME_MINOR_VERSION="0",
            TOOLKIT_FLAME_PATCH_VERSION="0",
            TOOLKIT_FLAME_PYTHON_BINARY=self.FLAME_2018_PYTHON,
        )
        return expected

    def _get_classic_args_2018(self):
        return (
            "'%s/python/startup/app_launcher.py' "
            "%s " % (repo_root, self.FLAME_2018_PATH)
        )

    def test_flame_2018(self):
        """
        Ensures Flame LaunchInformation is correct.
        """
        self._test_launch_information(
            "tk-flame",
            self.FLAME_2018_PATH,
            self._get_classic_environment_2018(),
            self._get_classic_args_2018()
        )

    def _test_launch_information(self, engine_name, dcc_path, expected_env, expected_args):
        """
        Validates that a given DCC has the right LaunchInformation.

        :param str engine_name: Name of the engine instance name to create a launcher for.
        :param str dcc_path: Path to the DCC.
        :param dict expected_env: Expected environment variables.
        :param str expected_args: Expected arguments.
        """
        flame_launcher = sgtk.platform.create_engine_launcher(
            self.tk, sgtk.context.create_empty(self.tk), engine_name, ["10.0v5"]
        )

        launch_info = flame_launcher.prepare_launch(dcc_path, "")

        self.assertEqual(
            expected_args,
            launch_info.args
        )

        # Ensure the environment variables from the LaunchInfo are the same as the expected ones.
        self.assertListEqual(
            sorted(expected_env.keys()),
            sorted(launch_info.environment.keys()),
        )

        # Ensure each environment variable's value is the same as they expected ones.
        for key, value in expected_env.iteritems():
            self.assertIn(key, launch_info.environment)
            self.assertEqual(launch_info.environment[key], value)
