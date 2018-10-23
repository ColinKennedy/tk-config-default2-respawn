## Adding Code To Respawn
Say for example, you have a Python module located in `~/my_modules/my_tool.py`
and you want `my_tool` to become importable in Nuke. The simplest way would be
to append the path to PYTHONPATH, directly. With Respawn, you can do this using
Rez's `package.py` file.

```bash
mkdir ~/my_modules
touch ~/my_modules/my_tool.py
```

Go to `{respawn_location}/rez_packages/nuke/11.2v3/package.py` and add
`env.PYTHONPATH.append('~/my_modules')` to the "commands" function.

Re-build the "nuke" packge by removing your `~/packages/nuke` folder
(Why `~/packages/nuke`? See [Local Package Installs](https://github.com/nerdvegas/rez/wiki/Building-Packages#local-package-installs)),
opening Shotgun Desktop, and clicking the Nuke icon. Once Nuke is loaded,
you can now run this Python command in the Script Editor.

```python
import my_tool
```

And that's all there is to it. The rest of this page will go over different
strategies to make appending environment variables easier but they're by no
means "required" to start appending paths to your packages immediately.


### Adding To Multiple Package Versions At Once
Adding code to the `package.py` file is nice but that can get easily out of
hand if you had, for example, 20 versions of different packages to update.

There needs to be a simple way to share code across different Rez packages.
Respawn comes with a Python package called "Rezzurect" which makes this easy.

Rezzurect is a series of Python classes which are shared across Rez
packages. It's a one stop stop that handles many things, including environment
variables and aliases.

In our previous example, pretend for a moment we wanted to make `my_tool.py`
available to all of our Nuke Rez packages across all of supported OSes.
To do this, open

`{respawn_location}/vendors/rezzurect/adapters/nuke/nuke_setting.py`

In there is a single class called "CommonNukeSettingAdapter". Add the same
`env.PYTHONPATH.append` command from before inside of it.


```python
class CommonNukeSettingAdapter(common_setting.BaseAdapter):

    # ... more code

    def execute(self):
        super(CommonNukeSettingAdapter, self).execute()

        env.PYTHONPATH.append('~/my_modules')
```

Now if you delete the `~/packages/nuke` folder, refresh Shotgun Desktop,
and load any version of Nuke, you can import your `my_tool.py`.

Note:
    The reason why we have to delete installed packages whenever we make
    changes to Rezzurect is because Respawn will only build Rez packages if they
	are not already installed. When a Rez package is built, Rezzurect gets
	copied placed into it so that the Rez package can stay self-contained.

    This is recommended for releasing and distributing packages but it
	can be a bit frustrating for developers. For temporary changes or development,
	it's a good idea to remove this feature so you can work quicker.
	See [Using A Shared Rezzurect Package](TODO URL Here) for details.


Important:
    If you want to set paths in different OSes, repeat the same steps but do it
    in `nuke_setting_{OSTYPE}.py` instead.
    (Example: Add it to `nuke_setting_windows.py` in the
    `WindowsNukeSettingAdapter` class, instead.)

For future reference, all Rez packages that share code will follow the same folder structure.
So if you're ever in-doubt about where to add aliases and environment
variables, just look in:

    `{respawn_location}/vendors/rezzurect/adapters/{package}/{package}_setting.py`


### Referencing Code Within The Respawn Configuration
In Shotgun, Pipeline Configurations can be hosted on-disk or on a git server
and cloned directly to the user's local machine.

According to [Shotgun's Documentation](https://support.shotgunsoftware.com/hc/en-us/articles/115000067493-Integrations-Admin-Guide),
if a Pipeline Configuration is cloned, it gets added to the user's local
directory and given a name automatically.

Root directories by OS:
```
OS X: ~/Library/Caches/Shotgun/<site_name>
Windows: %APPDATA%\Shotgun\<site_name>
Linux: ~/.shotgun/<site_name>
```

Like the previous example, imagine if we wanted to add `my_tool.py` directly
into the Respawn repo, and then add that path to PYTHONPATH.
How would we do that? Pipeline Configurations can be installed basically
anywhere so it would be difficult to define the path ahead of time.

The answer to this problem is to use Rezzurect.


Pretend `my_tool.py` was located at:

`{tk-config-default2-respawn}/my_module/my_tool.py`

To make sure we get the correct path no matter how the Pipeline Configuration
is cloned on-disk, we'll use the same syntax as before but also include a
fancy command that Rezzurect comes with.

```python
from ...utils import resolver


class CommonNukeSettingAdapter(common_setting.BaseAdapter):

    # ... more code

    def execute(self):
        super(CommonNukeSettingAdapter, self).execute()
        env.PYTHONPATH.append(resolver.expand('{respawn_root}/my_module'))
```

The path `'{respawn_root}/my_module'` will consistently expand to wherever your
Pipline Configuration is installed and still work as expected.

`{respawn_root}` is a pre-defined key that is defined to mean "wherever this
Pipeline Configuration is located". You can even define your own keys, which
can be used to refer to other locations on-disk.
See [Linking Code From Respawn](TODO URL HERE) for more details.


### Linking Code From Respawn
We have a way to add raw paths to environment variables. This is great for when we
have paths that aren't likely to change. We even can add these paths to
multiple packages at once.

We also have a way to add paths to files that are located inside of the
Pipeline Configuration, using keys.

But keys can be used for more than just referring to locations in your Pipeline
Configuration. You can use it to refer to anywhere on-disk.
This is extremely useful for developers, specifically.

Say for example you have a repository called `repository_a`. Multiple shows use
`repository_a` which is cloned to `/dir/to/repository_a` on a network and you
need to make some changes to it. To avoid working directly with
`/dir/to/repository_a` which is live-code, you clone a copy of `repository_a`
someplace else, like `~/my/dir/to/repository_a`.

If `/dir/to/repository_a` was hard-coded into all of your Rez package.py files,
as `env.PYTHONPATH.append('/dir/to/repository_a')` then you'd now
have to search-and-replace that string and change it to `~/my/dir/to/repository_a`.

Obviously that's a huge time-sink and a lot to keep track of.

But if you use a key instead, like `env.PYTHONPATH.append(resolver.expand('{a_root}'))`
then all you have to do is change where `'{a_root}'` points to.

So how do you add your own key?


#### Adding Custom Keys
Adding and managing keys can be done a number of different ways.

You can set keys from the Shotgun Web App, include them directly inside of your
Pipeline Configuration, or set keys only for your user.


##### From a .respawnrc file
A .respawnrc file is a JSON or YAML file that defines data which Respawn needs
to run. Here is an example:

```yaml
keys:
    a_root: /dir/to/repository_a
```


##### Adding Keys With A Pipeline Configuration
Add the .respawnrc file to wherever your tk-confid-default2-respawn folder
is installed at `{respawn_location}/.respawnrc` and the key is now defined
for that Pipeline Configuration.


##### Adding Keys With Shotgun
The .respawnrc config file is simple and convenient but it has a major flaw.
If you need to distribute a beta, you'd have to make a complete copy of Respawn
just to change maybe one or two paths in the .respawnrc file to the
new beta location.

To avoid having to do that, Respawn lets you add keys from the Shotgun Web App.

Setup:
1. Create a dict, write in all your keys, and then convert it into a JSON string
2. Add a new Field to the Pipeline Configuration Entity and call it "respawn_keys"
3. Paste in your JSON string into its "respawn_keys" Field.

Now you can create multiple Pipeline Configurations that use the same
repository but have them point to completely different code-bases, right from the Shotgun
Web App.


##### Adding Keys With A User File
If you are running or building Rez packages from command-line, you won't have a
Shotgun Toolkit context to be able to get your keys. In these circumstances,
the best thing to do is to make a .respawnrc like so:

```yaml
keys:
    a_root: ~/my/dir/to/repository_a
```

And then add it to your user folder:

```
Linux/Mac: ~/.respawnrc
Windows: %USERPROFILE%\.respawnrc
```

Now Respawn will pick up keys defined there and you won't have to change a
Pipeline Configuration in Shotgun or the repository's .respawnrc to do it.


### Key Load Order
The different methods listed above load in the following order (from first to last).

- Pipeline Configuration's .respawnrc file
- Shotgun "respawn_keys" Field
- ~/.respawnrc file

Note:
    When keys are loaded, they are "stacked" accumulatively. For example, if a
    key named "foo" is defined in Shotgun but not defined in ~/.respawnrc,
    "foo" will still exist. It will just fallback to the Shotgun entry.

    To delete the "foo" key, you must set `foo: ""` in one of the later loading methods.


### Which Key Method To Use
Shotgun and the different .respawnrc file locations each have their own
advantages and disadvantages. Generally speaking, it's best to avoid using
Shotgun to set keys because that will make it harder to build and test Rez
packages without being tied to the Shotgun Environment.

But even if you do choose to prefer Shotgun, if needed, you can always override
those values with your personal `~/.respawnrc` file, if needed.

The Pipeline Configuration `.respawnrc` file is good to keys that won't change
or are unlikely to change. Shotgun is great for making Pipeline Configurations
where you might have one Project use one set of keys or maybe you've got one
user on a project testing a beta for you so you give that user a Pipeline
Configuration with another set, etc. etc. Shotgun makes it very easy to set
keys at the per-project and per-user level so keys that tend to change often
should go there.

You can even have a Pipeline Configuration set to only your user and prefer to
set your keys there, instead of using a personal `~/.respawnrc` file.

Here is a flowchart to summarize:


                       +---------------------------------+
                       |                                 |
                       |    Is the override meant for    |
                   +---+  your user or multiple people?  +-------+
                   |   |                                 |       |
                   |   +---------------------------------+       |
                   +                                             +

                Just me                                   Multiple people

                   +                                             +
                   |                                             |
                   |                                             |
                   |                                             |
   +---------------+--------------+              +---------------+----------------+
   |                              |              |                                |
   |  Is the override temporary?  |              |  Do you need to make multiple  |
   |                              |              |        override variants?      |
   +--+------------------------+--+              |                                |
      |                        |                 +--+--------------------------+--+
      |                        |                    |                          |
      +                        +                    +                          +

      No                      Yes                   No                        Yes

      +                        +                    +                          +
      |                        |                    |                          |
      |                        |                    |                          |
      |                        |                    |                          |
      |                        |                    |                          |
      |                        |                    |                          |
+-----+-----+         +--------+-------+            |                    +-----+-----+
|Use Shotgun|         |Use ~/.respawnrc|            |                    |Use Shotgun|
+-----------+         +----------------+            |                    +-----------+
                                                    |
                                                    |
                                                    |
                                                    |
                                       +------------+---------------+
                                       |Use Configuration .respawnrc|
                                       +----------------------------+


##### Advanced: Descriptors And Respawn Keys
TODO : Need to write this
