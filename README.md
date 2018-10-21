This is a WIP, experimental repository for a VFX studio pipeline. It is
a Pipeline Configuration that is based on
[tk-config-default2](https://github.com/shotgunsoftware/tk-config-default2), a
sample repository made by Shotgun Software.

Respawn is still very early in development but, at its core, it's a
proof-of-concept based on a google group post about
[using Shotgun and Rez](https://groups.google.com/forum/#!topic/rez-config/U1wFOH_DHiM).

This repository and its submodules are an attempt to provide an "out-of-box"
way to use Rez with Shotgun with a very minimal setup.


## Project Goals
1. Auto installation

The process to install this repository as a Pipeline Configuration should be
kept as simple as possible. In the ideal case, any user with Shotgun Desktop
installed should be able to log in, press a button to open a package (like Houdini,
Maya, Nuke, etc.) and be able to get started without fuss or worry.

2. Zero-config setup

Zero-config means that the pipeline should be able to be able
to initialize, build, and run itself without user intervention.

Where "Auto installation" meant to benefit artists, "Zero-config setup" is
meant to benefit Pipeline TDs. Software deployment should be painless and
(ideally) fast. This goal comes from the desire to make deployment simpler
and relieve tired TDs of traditional, manual deployment processes and put power
back in their hands.

3. Distributable packages

The software provided by this repository should run completely independently
from what the user has installed locally on their system.

Well-designed Rez packages promise this this functionality but the difference
between Respawn and a traditional Rez setup is that the Rez packages can be
bundled into Respawn directly or it can be referenced from a network location.

Respawn promises that its packages will remain self-contained in order
to take full advantage of Rez but also allow those packages to be distributed
as part of Pipeline Configurations.

4. Single-description Rez packages

Rez supports multiple build systems such as cmake and even comes with its own,
called bez. The bez build system is an interesting option because it has a low
barrier of entry. That said, bez is not feature-rich and its instructions tend
to vary greatly per-package. Respawn aims to try to make bez more generic
and easier to maintain.


# Installation
TODO Check back. This is still WIP so the steps would change too frequently anyway.


# Working with Respawn
This guide is meant for people who are mainly responsible for troubleshooting
issues with the configuration as well as adding and updating new software. It
assumes knowledge of [Shotgun](https://www.shotgunsoftware.com/) and
[Git-SCM](https://git-scm.com/).


## Making A Work Area
A work area is a place on-disk where you can freely make changes and develop
tools without worrying breaking anything in production. Creating your own work
area is simple enough.

Here are the steps to make your own work area:

- Clone this repository

```bash
git clone --recursive https://github.com/ColinKennedy/tk-config-default2-respawn.git ~/some/folder/tk-config-default2-respawn
```

- Log onto your Shotgun website and add a new Pipeline Configuration entry to
  your own user, set to the following:

```
sgtk:descriptor:dev?path=~/some/folder/tk-config-default2-respawn
```

Now you are sourcing your clone of the repository and can make changes to it.
Those changes will be reflected in Shotgun Desktop, as well.

Once that's done, you should be able to load the Pipeline Configuration for
a Project in Shotgun Desktop, click on any one of the software shown,
and immediately begin to download, install, and use the software.


### Developer Best Practices
It's a good idea to make a fork of Respawn and make any specific changes that
you'll need to work with it.

For example, Rez tries to release packages to the "~/.rez/packages/int" folder
but most likely, you'll need that location to be somewhere on your network.

You have the choice to set the `REZ_CONFIG_FILE` enviroment variable to
wherever Respawns's .rezconfig file is located, like so:

```bash
export REZ_CONFIG_FILE=~/some/folder/tk-config-default2-respawn/rez_packages/.rezconfig
```

and then add the following to the .rezconfig file:

```yaml
release_packages_path: "/network/location/shared/by/everyone"
```

This is the recommended way to work because it means that you can work exactly
how you'd like and, once you're ready to release a package, simply release the
packages located in Respawn and any Shotgun Project also sourcing Respawn will
immediately get those updates.

If you need to support multiple configs or don't want to edit the .rezconfig
file in Respawn, you can also simply override the `REZ_RELEASE_PACKAGES_PATH`
environment variable. Just note that if you do this, `REZ_RELEASE_PACKAGES_PATH`
will take priority over the .rezconfig file. See
[Configuring Rez Overview](https://github.com/nerdvegas/rez/wiki/Configuring-Rez#overview)
and [System Environment Variables](https://github.com/nerdvegas/rez/wiki/Environment-Variables#system-environment-variables) for details.


# Maintainence
## Adding New Software
By default, Shotgun "finds" software versions by checking the user's disk for
installed software in its default locations.

For example, if you look at bundle_cache/app_store/tk-nuke/{version}/startup.py,
you'll see that the `_find_software` method has been overwritten to find
software versions by looking at Rez packages for Nuke. However, if you look at
software that is not supported by Rez, the `_find_software` method would
typically just check paths until if found some installed file.

If you want to add new software in the future, you'll need to search for
versions by looking for Rez packages the same way.


# Getting Started
First, before reading further, check out
[the Rez guide for building packages](https://github.com/nerdvegas/rez/wiki/Building-Packages).
It's extensive and goes over basically everything you need to know.


## How to quickly port pip (pypi) packages
Describe how to move rez packages outside of a pipeline configuration


# Current Caveats
Currently, Rez needs to be installed on people's machines beforehand in order to run.
This will hopefully be fixed in the future.


# Road Map
0.4.0
- Write documentation on deployment
 - In particular - Recursive deployment of a package should be a "one-button" solution
 - Make a tool (probably a CLI) that can recursively release a package unless
   this can be done with Rez out-of-box

0.5.0
- Get it to work with Houdini

0.6.0
- Make it so that Rez does not need to be installed onto the user's machine
  in order for it to be used


# Project Checklist (TODO)
- Check to see if aliases work on Windows and Linux
 - Aliases in Windows don't work on command-line. BUt what about through Python?
 - And if not, what are "tools" and can I use those?
- Add Houdini and Maya Support
- Research rez-release (grok it)
- Build various ways to ...
 - Have a config file location in the Configuration which can be used to point
   to a shared root(s) for Python packages
 - Look into custom descriptors (or maybe an extra field) so that I can possibly 
   parse more information, from Shotgun, about package information. That way, 
   a developer can customize how software resolves and limit software versions
   without having to make a fork of the configuration!
   - Or set-able from the configuration file, too
- Make "trackable" env vars
 - Once I have a MVP, post on rez-config to see if there is a better way
- Find out how to unittest this repo. Shotgun authentication will probably be required...
- Shotgun forces a build to fail repeatedly even if the original error has been fixed (i.e. retrying a build after deleting a package folder will still fail.)
 - The only way to make it work again is to exit the Shotgun Project and go back in again. See if there's a way to avoid having to do that
- Find a way to make it easy to work with a "live production deployment" so
  that users can immediately get updates without restarting their DCC
- Make a tool that can clear a package and install it from scratch (even if it
  is already previously installed)
- FlexLM licensing R&D

- Make Internet download progress log better
 - Possibly: https://blog.shichao.io/2012/10/04/progress_speed_indicator_for_urlretrieve_in_python.html

- R&D aliases. Maybe they can be used instead of raw commands? That'd be ideal.
 - If I can get them to work on Windows and Linux, remove all of the "setting adapter"
   logic, replace it with just "main", and then update `__rez_runner.py` to just
   call "main".
- Also figure out how to add rez (the python package). Very important obviously
- Using `config_package_root` may not work for deployment. Double-check this TD117


## Development Documentation TODO
These are TODO notes that I thought of while writing docs for Respawn.

This part:

	`{respawn_root}` is a special key that is defined to mean "wherever the top of
	this Pipeline Configuration is". You can even define your own keys to refer to
	other locations on-disk

Make it so that users can define their own keys and they can also define keys
which are based on other keys.

Add "Quick checklist" for common operations so that people can see very concise
summaries of what to do for certain things. Explanations are good but make it
difficult to reference, later.

- Add a way to automatically add ways to add .respawnrc files

- Create a way to make compound software packages
 - like "maya and vray1.9"
 - or "maya and vray >1.9 <2.1"

- Make sure to write a page to explain the "{DCC}_installation" repositories
  and why they are necessary
