# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os

def appExit( info ):
    import sgtk
    engine = sgtk.platform.current_engine()

    # Nothing to do if no Shotgun engine has been initialized.
    if engine is not None:
        engine.destroy()


def getCustomUIActions():

    version = [os.environ.get("SHOTGUN_FLAME_MAJOR_VERSION"), os.environ.get("TOOLKIT_FLAME_MAJOR_VERSION")]
    major_version = next((v for v in version), None)

    if major_version is not None and int(major_version) >= 2018:
        # Bypass getCustomUIActions contextual hook from version 2018.
        # More recent version will use the main menu instead.
        return ()

    return getMainMenuCustomUIActions()

def getMainMenuCustomUIActions( ):
    """
    Hook returning the custom ui actions to display to the user in the contextual menu.

    :returns: a tuple of group dictionaries.

    A group dictionary defines a custom menu group where keys defines the group.

    Keys:
        name: [String] Name of the action group that will be created in the menu.
        actions: [String] Tuple of action dictionary which menu items will be created in the group.

    An action dictionary of userData where the keys defines the action

    Keys:
        name: [String] Name of the action that will be passed on customUIAction callback.
        caption: [String] Caption of the menu item.

    For example: 2 menu groups containing 1 custom action each:

    return (
        {
            "name": "Custom Group 1",
            "actions": (
                {"name": "action1", "caption": "Action Number 1"},
            )
        },
        {
            "name": "Custom Group 2",
            "actions": (
                {"name": "action2", "caption": "Action Number 2"},
            )
        },
    )
    """
    # first, get the toolkit engine
    import sgtk
    engine = sgtk.platform.current_engine()

    # We can't do anything without the Shotgun engine. 
    # The engine is None when the user decides to not use the plugin for the project.
    if engine is None:
        return ()

    # build a list of the matching commands
    # returns a list of items, each a tuple with (instance_name, display_name, name, callback)
    commands = engine._get_commands_matching_setting("context_menu")

    # Commands are uniquely identified by command name and by display name so build a list of them
    context_commands = []
    for (instance_name, display_name, command_name, callback) in commands:
        context_commands.append((command_name, display_name))



    # now add any 'normal' registered commands not already in the actions dict
    # omit system actions that are on the context menu
    context_command_names = [context_command[0] for context_command in context_commands]
    for engine_command_name in engine.commands:
        properties = engine.commands[engine_command_name]["properties"]
        if engine_command_name not in context_command_names and properties.get("type") != "context_menu":
            context_command_names.append(engine_command_name)
            context_commands.append((engine_command_name, engine_command_name))

    # do not add the menu if there are no matches
    if not context_commands:
        return ()

    # sorts the list to have Log out option always appear last, Shotgun Python Console prior, and the rest in same order
    context_commands.sort(key=lambda el: ('Log Out' in el, 'Shotgun Python Console...' in el, None))

    # generate flame data structure
    actions = [{"name": command_name, "caption": display_name} for (command_name, display_name) in context_commands]

    return (
        {
            "name": "Shotgun",
            "actions": tuple(actions)
        },
    )


def customUIAction(info, userData):
    """
    Hook called when a custom action is triggered in the menu

    :param info: A dictionary containing information about the custom action with the keys
                 - name: Name of the action being triggered
                 - selection: Tuple of wiretap ids

    :param userData: The action object that was passed to getCustomUIActions
    """
    # first, get the toolkit engine
    import sgtk
    engine = sgtk.platform.current_engine()

    # We can't do anything without the Shotgun engine. 
    # The engine is None when the user decides to not use the plugin for the project.
    if engine is None:
        return

    # get the comand name
    command_name = info["name"]
    # find it in toolkit
    command_obj = engine.commands.get(command_name)

    # execute the callback if found
    if command_obj:
        command_obj["callback"]()
