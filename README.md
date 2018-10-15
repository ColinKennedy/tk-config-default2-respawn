This is a WIP, experimental repository for a VFX studio pipeline. It is
a Pipeline Configuration that is based on
[tk-config-default2](https://github.com/shotgunsoftware/tk-config-default2), a
sample repository made by Shotgun Software.

Respawn is still very early in development but, at its core, it's a
proof-of-concept based on a google group post about
[using Shotgun and Rez](https://groups.google.com/forum/#!topic/rez-config/U1wFOH_DHiM).

Together the 3 tools, Shotgun, Rez, and Respawn take on the following roles:
- Shotgun is used as a distribution mechanism (as is intended)
- Rez is used to configure and run software in self-described containers
- Respawn is used to source Rez packages and make them available to the artist
  automatically. And, where necessary, it can be used to forcibly build Rez packages


## Project Goals
1. Auto installation

The process to install this repository as a Pipeline Configuration should be
kept as simple as possible. In the ideal case, any user with Shotgun Desktop
installed should be able to log in, press a button to a package (like Houdini,
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


# Project Checklist (TODO)
- Make it work in Windows, too
- Get it to work with Nuke
 - Confirm link
 - Confirm internet
- Figure out deployment
- Find a way to make it easy to work with a "live production deployment" so
  that users can immediately get updates without restarting their DCC
- Get it to work with Houdini
- Make a tool (probably a CLI) that can recursively release a package!
- Make a tool that can clear a package and install it from scratch (even if it
  is already previously installed)
- Include Rez as part of the rez packages (so that we make sure that Rez is installed).
- FlexLM licensing R&D

- R&D aliases. Maybe they can be used instead of raw commands? That'd be ideal.
 - If I can get them to work on Windows and Linux, remove all of the adapter
   logic for creating the "main run" command and update `__rez_runner.py` to just
   call "main".
- Also figure out how to add rez (the python package). Very important obviously
- Using `config_package_root` may not work for deployment. Double-check this TD117
