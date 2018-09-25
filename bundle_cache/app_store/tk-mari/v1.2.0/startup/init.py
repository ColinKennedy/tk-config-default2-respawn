# Copyright (c) 2014 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.


import os
import mari

def show_warning(msg):
    """
    Show the specified warning to the user - if in UI mode then also show a
    message box
    
    :param msg:    The warning message to show
    """
    warning_msg = "Shotgun Warning: %s" % msg 
    print warning_msg
    if not mari.app.inTerminalMode():
        mari.utils.misc.message(warning_msg, "Shotgun Warning")


def bootstrap_sgtk():
    """
    Bootstrap sgtk as part of the Mari initialisation:
    """
    try:
        import sgtk
    except Exception, e:
        show_warning("Could not import sgtk! Disabling for now: %s" % e)
        return
    
    if not "TANK_ENGINE" in os.environ:
        # key environment missing.
        return
    
    engine_name = os.environ.get("TANK_ENGINE")
    try:
        context = sgtk.context.deserialize(os.environ.get("TANK_CONTEXT"))
    except Exception, e:
        show_warning("Could not create context! Shotgun Pipeline Toolkit will be disabled. Details: %s" % e)
        return

    try:    
        engine = sgtk.platform.start_engine(engine_name, context.sgtk, context)
    except Exception, e:
        show_warning("Could not start engine: %s" % e)
        return
    
    # clean up temp env vars
    for var in ["TANK_ENGINE", "TANK_CONTEXT", "TANK_FILE_TO_OPEN"]:
        if var in os.environ:
            del os.environ[var]

bootstrap_sgtk()