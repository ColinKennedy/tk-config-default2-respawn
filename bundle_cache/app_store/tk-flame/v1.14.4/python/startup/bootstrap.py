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
import os
import re
import sys

# NOTE: This bootstrap process is left in place for legacy purposes. It
# will be used by older versions of the tk-multi-launchapp app from
# prior to the release of Software entity launchers. Much of the logic
# in this script has been reproduced in tk-flame/startup.py as part of
# the classic configuration launch process.

def _get_flame_version(flame_path):
    """
    Returns the version string for the given Flame path
    
    <INSTALL_ROOT>/flameassist_2016.2/bin/startApplication        --> (2016, 2, 0, "2016.2")
    <INSTALL_ROOT>/flameassist_2016.3/bin/startApplication        --> (2016, 3, 0, "2016.3")
    <INSTALL_ROOT>/flameassist_2016.0.3.322/bin/startApplication  --> (2016, 0, 3, "2016.0.3.322")
    <INSTALL_ROOT>/flameassist_2016.2.pr99/bin/startApplication   --> (2016, 2, 0, "2016.2.pr99")
    <INSTALL_ROOT>/flame_2016.pr50/bin/start_Flame                --> (2016, 0, 0, "2016.pr50")

    If the patch, minor or major version cannot be extracted, it will be set to zero.

    :param flame_path: path to executable
    :returns: (major, minor, patch, full_str)
    """

    # do a quick check to ensure that we are running 2015.2 or later
    re_match = re.search("/fla[mr]e[^_]*_([^/]+)/bin", flame_path)
    if not re_match:
        raise TankError("Cannot extract Flame version number from the path '%s'!" % flame_path)
    version_str = re_match.group(1)

    # Examples:
    # 2016
    # 2016.2
    # 2016.pr99
    # 2015.2.pr99

    major_ver = 0
    minor_ver = 0
    patch_ver = 0

    chunks = version_str.split(".")
    if len(chunks) > 0:
        if chunks[0].isdigit():
            major_ver = int(chunks[0])

    if len(chunks) > 1:
        if chunks[1].isdigit():
            minor_ver = int(chunks[1])

    if len(chunks) > 2:
        if chunks[2].isdigit():
            patch_ver = int(chunks[2])

    return (major_ver, minor_ver, patch_ver, version_str)


def bootstrap(engine_instance_name, context, app_path, app_args):
    """
    Entry point for starting this engine.
    This is typically called from something like tk-multi-launchapp
    prior to starting up the DCC, but could be initialized in other ways too.

    This method needs to be able to execute from any python version, with
    or without QT installed. Since it will typically be executed from within
    the multi-launch-app, it will be running in the python that was used to
    start the engine where the multi-launch-app is running (typically
    tk-shell/tk-desktop/tk-shotgun).

    The purpose of this script is to prepare the launch process for Flame,
    return the executable that the launch app should actually execute. This
    process consists of an additional step for Flame because part of the app
    launch process happens outside of Flame. We therefore rewrite the launch
    arguments as part of this method. For example

    input: app_path: <INSTALL_ROOT>/flame_2015.2/bin/startApplication
           app_args: --extra args

    output: app_path: <INSTALL_ROOT>/Python-2.6.9/bin/python
            app_args: /mnt/software/shotgun/my_project/install/engines/app-store/tk-flame/v1.2.3/python/startup/launch_app.py
                      <INSTALL_ROOT>/flame_2015.2/bin/startApplication
                      --extra args

    :param engine_instance_name: the name of the engine instance in the environment to launch
    :param context: The context to launch
    :param app_path: The path to the DCC to start
    :param app_args: External args to pass to the DCC

    :returns: (app_path, app_args)
    """

    # Get the realpath because central install builds are started with a symlink to the launcher script
    # ex: /usr/tmp/flame_232/Flame -> /opt/Autodesk/flame_2017.1.0.232/bin/start_Flame
    # so the real path will return /usr/tmp/flame_232/opt/Autodesk/flame_2017.1.0.232/bin/start_Flame
    # which can be parsed with the same regexp than local installation path.
    app_path = os.path.realpath(app_path)

    # do a quick check to ensure that we are running 2015.2 or later
    (major_ver, minor_ver, patch_ver, version_str) = _get_flame_version(app_path)

    if major_ver < 2016:
        raise TankError("In order to run the Shotgun integration, you need at least Flame 2016!")

    # first of all, check that the executable path to Flame exists
    if not os.path.exists(app_path):
        raise TankError("Cannot launch the Flame/Flare integration environment - the path '%s' does not exist on disk!" % app_path)

    # update the environment prior to launch
    os.environ["TOOLKIT_ENGINE_NAME"] = engine_instance_name
    os.environ["TOOLKIT_CONTEXT"] = sgtk.context.serialize(context)

    # ensure that we add the right location for the wiretap API.
    # on 2016 and above, we can use the one distributed with Flame
    # in 2016: /usr/discreet/flameassist_2016.0.0.322/python

    wiretap_path = None
    install_root = None

    # grab <INSTALL_ROOT>/<APP_FOLDER> part of the path and then append python
    re_match = re.search("(^.*)/(fla[mr]e[^_]*_[^/]+)/bin", app_path)
    if not re_match:
        raise TankError("Cannot extract install root from the path '%s'!" % app_path)
    else:
        install_root = re_match.group(1)
        app_folder = re_match.group(2)

        wiretap_path = os.path.join(install_root, app_folder, "python" )

    sgtk.util.prepend_path_to_env_var("PYTHONPATH", wiretap_path)

    # also, in order to ensure that QT is working correctly inside of
    # the Flame python interpreter, we need to hint the library order
    # by adjusting the LD_LIBRARY_PATH. Note that this cannot be done
    # inside an executing script as the dynamic loader sets up the load
    # order prior to the execution of any payload. This is why we need to
    # set this before we run the app launch script.
    if sys.platform == "darwin":
        # add system libraries
        sgtk.util.prepend_path_to_env_var(
            "DYLD_FRAMEWORK_PATH",
            "%s/lib64/%s/framework" % (install_root, version_str)
        )

    elif sys.platform == "linux2":
        # add python related libraries

        # on Flame, each version is managed separately
        sgtk.util.prepend_path_to_env_var("LD_LIBRARY_PATH", "%s/python/%s/lib" % (install_root, version_str))

        # add system libraries
        sgtk.util.prepend_path_to_env_var("LD_LIBRARY_PATH", "%s/lib64/%s" % (install_root, version_str))

    # figure out the python location
    python_binary = "%s/python/%s/bin/python" % (install_root, version_str)

    # we need to pass the Flame version into the engine so that this
    # can be picked up at runtime in the Flame. This is in order for
    # the engine to resolve the path to python.
    os.environ["TOOLKIT_FLAME_PYTHON_BINARY"] = python_binary

    # also pass the version of Flame in the same manner
    os.environ["TOOLKIT_FLAME_MAJOR_VERSION"] = str(major_ver)
    os.environ["TOOLKIT_FLAME_MINOR_VERSION"] = str(minor_ver)
    os.environ["TOOLKIT_FLAME_PATCH_VERSION"] = str(patch_ver)
    os.environ["TOOLKIT_FLAME_VERSION"] = version_str

    # and the install location
    os.environ["TOOLKIT_FLAME_INSTALL_ROOT"] = install_root

    # the app_launcher.py script is in the same folder as this file
    this_folder = os.path.abspath(os.path.dirname(__file__))
    launch_script = os.path.join(this_folder, "app_launcher.py")

    # finally, reroute the executable and args and return them
    # (see docstring for details)
    new_app_path = python_binary
    new_app_args = "'%s' %s %s" % (launch_script, app_path, app_args)

    return (new_app_path, new_app_args)