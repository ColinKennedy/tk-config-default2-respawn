#!/usr/bin/env python

# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

# This script is called from the engine method create_local_backburner_job().
# It is executed by the backburner farm dispatcher and assumes only a basic
# python environment is present. All other data is pulled up from a 
# pickle inside a temporary file which is passed as the single argument when
# this script is called.

# typically, the following sort of command line is generated in create_local_backburner_job():
# /usr/discreet/backburner/cmdjob 
# -userRights 
# -jobName:"Sequence 'aa002' - Uploading media to Shotgun" 
# -description:"Creates a new version record in Shotgun and uploads the associated Quicktime." 
# -servers:Mannes-MacBook-Pro-2.local 
# -dependencies:1587902041 
# /usr/discreet/Python-2.6.9/bin/python 
# /Users/manne/git/tk-flame/python/startup/backburner.py 
# /var/folders/fq/65bs7wwx3mz7jdsh4vxm34xc0000gn/T/tk_backburner_f6a70d85fecf420a979357c9d9dd9278.pickle

# this script will unpack the pickle parameters file, add sgtk to the pythonpath, 
# start an engine and finally run an app or engine hook method.

import os
import sys
import pickle

pickle_file = sys.argv[1]

if not os.path.exists(pickle_file):
    raise IOError("Cannot find backburner command file '%s'!" % pickle_file)

fh = open(pickle_file, "rb")
data = pickle.load(fh)
fh.close()

# get the data out of our pickle
sgtk_core_location = data["sgtk_core_location"]
serialized_context = data["serialized_context"]
engine_instance = data["engine_instance"]
instance = data["instance"]
method_to_execute = data["method_to_execute"]
method_args = data["args"]
flame_version = data["flame_version"]
user_home = data["user_home"]

# Make sure that the job is running with the good home
os.environ["HOME"] = user_home

# add sgtk to our python path
sys.path.append(sgtk_core_location)
import sgtk

# first, attempt to launch the engine
context = sgtk.context.deserialize(serialized_context)

# set a special environment variable to help hint to the engine
# that we are running a backburner job
os.environ["TOOLKIT_FLAME_ENGINE_MODE"] = "BACKBURNER"

# set the flame version environment variable to ensure that the pick environment select the right config
os.environ["SHOTGUN_FLAME_MAJOR_VERSION"] = flame_version["major"]
os.environ["SHOTGUN_FLAME_MINOR_VERSION"] = flame_version["minor"]
os.environ["SHOTGUN_FLAME_PATCH_VERSION"] = flame_version["patch"]
os.environ["SHOTGUN_FLAME_VERSION"] = flame_version["full"]

engine = sgtk.platform.start_engine(engine_instance, context.sgtk, context)
engine.set_version_info(major_version_str=flame_version["major"], minor_version_str=flame_version["minor"],
                        patch_version_str=flame_version["patch"], full_version_str=flame_version["full"])
del os.environ["TOOLKIT_FLAME_ENGINE_MODE"]
engine.log_debug("Engine launched for backburner process.")

# get the app from the instance_name
app = engine.apps.get(instance, None)

# if the instance is an app, execute the method
if app:
    method = getattr(app, method_to_execute)
    engine.log_debug("Executing remote callback for app instance %s (%s)" % (instance, app))
    engine.log_debug("Executing callback %s with args %s" % (method, method_args))

    method(**method_args)
# if the instance is not an app, it's a hook
else:
    engine.log_debug("Executing remote callback for hook %s" % instance)
    engine.log_debug("Executing callback %s with args %s" % (method_to_execute, method_args))
    engine.execute_hook_method(instance, method_to_execute, **method_args)

# all done
engine.log_debug("Backburner execution complete.")

# clean up
try:
    engine.log_debug("Trying to remove temporary pickle job file...")
    os.remove(pickle_file)
    engine.log_debug("Temporary pickle job successfully deleted.")
except Exception, e:
    engine.log_warning("Could not remove temporary file '%s': %s" % (pickle_file, e))
