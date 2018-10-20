This section assumes prior, beginner knowledge of Rez. If you have not already,
read through the [Basic Concepts](https://github.com/nerdvegas/rez/wiki/Basic-Concepts)
and [Package Definition Guide](https://github.com/nerdvegas/rez/wiki/Package-Definition-Guide)
so that you can better understand this page.

Also, Respawn assumes basic administrator knowledge of [Shotgun](https://www.shotgunsoftware.com/).
In particular, review Shotgun's [Cloud Configuration Webinar](https://www.youtube.com/watch?v=5nRZ5GgcOnk&list=PL9f6R0sm_zAzLLByryYL3bHcbHKMmS-9o&index=8)
and review the "Software" Entity and how it works.


## Initial Setup
This section and its sub-sections can be seen as a "Getting Started" guide.
Information that provided here only needs to be configured one time.

The main bits of information to understand are that Respawn doesn't know about
your studio's pipeline. This section goes over how to quickly make Respawn
work, in its default state. Other sections will go over specifics on how to
hook Respawn into your studio's existing tools. See [Adding Code](TODO URL HERE)
for advanced details on that.


### Making A Local Work Area
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

Now, when you reload Shotgun Desktop, you'll be sourcing the cloned Pipeline
Configuration. This configuration comes with Rez packages and Software built in.
In the next sections, we'll talk about how to control which Rez Packages and
Software are shown to the user.


### Setting A Deployment Area
By default, Rez uses two package paths. One is your development / staging area
and the other path is used for releases.

When you're done writing a Rez package, you're probably going to want Rez to
build that package on a network location where others can access and use it.

Rez has a lot of documentation already on how to do this so I'll drop links here:
[Commandline Tool](https://github.com/nerdvegas/rez/wiki/Configuring-Rez#commandline-tool)
[release packages path](https://github.com/nerdvegas/rez/wiki/Configuring-Rez#release_packages_path)
[packages path](https://github.com/nerdvegas/rez/wiki/Configuring-Rez#packages_path)

To set up Respawn to some internel release path, simply create a new
file called `~/.rezconfig` and add this line to  it:

```yaml
release_packages_path: /some/network/location
```

Now add the same line to the Respawn's .rezconfig file, which is located at
`{respawn_location}/rez_packages/.rezconfig`.

By adding the same path to Respawn as your user, it means that your can deploy
packages at any time from the command-line and our Pipeline Configurations will
immediately pick up your changes.

Once you have written a package and want to to deploy it, head over to the
[Deploying Packages](TODO: URL HERE) page to learn how.


# Use Rez with standalone tools


# Getting Started
## Getting Started - The Simplest Setup


