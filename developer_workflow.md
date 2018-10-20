This section assumes prior, beginner knowledge of Rez. If you have no
already, read through the [Basic Concepts](https://github.com/nerdvegas/rez/wiki/Basic-Concepts)
and [Package Definition Guide](https://github.com/nerdvegas/rez/wiki/Package-Definition-Guide)
so that you can better understand this page.

Also, Respawn assumes basic administrator knowledge of [Shotgun](https://www.shotgunsoftware.com/).
In particular, review Shotgun's [Cloud Configuration Webinar](https://www.youtube.com/watch?v=5nRZ5GgcOnk&list=PL9f6R0sm_zAzLLByryYL3bHcbHKMmS-9o&index=8)
and review the "Software" Entity and how it works.


## Making A Local Work Area
One of the first things that a developer would want to do when starting with
Respawn is to know how to clone it and experiment without affecting production.
This section will go over how to do that and also a few ways that Respawn can
be integrated into existing pipelines.

First, clone Respawn to somewhere on-disk.

```bash
git clone --recursive https://github.com/ColinKennedy/tk-config-default2-respawn.git
```

Next, add a new Pipeline Configuration to your Shotgun site, give it a name
like "Dev", and assign the Configuration to yourself. Lastly, add the path to
wherever you installed the Configuration into Shotgun's "Descriptor" Field.


```
sgtk:descriptor:dev?path=/path/to/where/you/cloned/tk-config-default2-respawn
```

Note:
	From here on out the guide, to keep paths concise,
	`/path/to/where/you/cloned/tk-config-default2-respawn` will be referred to
	as `{respawn_location}`

Now, when you reload Shotgun Desktop, you'll be sourcing the cloned Pipeline
Configuration. The question now is, how to begin adding your code to Respawn.


## A Quick Explanation About Respawn's Rez Packages
When you load Shotgun Desktop in Respawn for the first time, you'll notice that
several software packages and versions are provided by default.

Shotgun's provided Pipeline Configuration, tk-config-default2, shows the user's
installed software as available options. Respawn works the same way but,
instead of searching for installed software, Respawn searches for packages
found in the `{respawn_location}/rez_packages` folder. That way, anything that
the user clicks on is actually being controlled by Rez package, under the hood.

Any folder that contains the following structure

`{respawn_location}/rez_packages/{package_name}/{package_version}/package.py`
will be picked up as an available Rez package.

In later sections, we will go over how to write a package from scratch and add
it to Shotgun Desktop. For now though, lets check out how to extend existing
packages.


## Referencing Pipeline Tools From Outside Of Respawn
### Referencing With A Config File
priority
 - config
 - user-config
 - env var
 - from Shotgun


# Deploying


# Ways Of Applying Respawn
## filter software by-project and by-user etc.

# Use Rez with standalone tools


# Getting Started
## Getting Started - The Simplest Setup


