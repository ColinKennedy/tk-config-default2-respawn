## Adding Code To Respawn
Say for example, you have a Python module located in `~/my_modules/my_tool.py`
and you want `my_tool` to become importable in Nuke. The simplest way would be
to append the path to PYTHONPATH, directly. With Respawn, you can do using
Rez's `package.py` file.

```bash
mkdir -p ~/my_modules
touch ~/my_modules/my_tool.py
```

Go to `{respawn_location}/rez_packages/nuke/11.2v3/package.py` and add
`env.PYTHONPATH.append('~/my_modules')` to the "commands" function.

Refresh Shotgun Desktop and click the Nuke icon. Once Nuke is loaded, you can
now run this Python command in the Script Editor

```python
import my_tool
```

And that's all there is to it.


### Adding To Multiple Package Versions At Once
Adding code to the `package.py` file is nice but that can get easily out of
hand if you had, for example, 20 versions of different packages to update.

There needs to be a simple way to share code across different Rez packages.
And there's where a Python helper library called "Rezzurect" comes in.

Rezzurect is a series of Adapter Python classes which are shared across Rez
packages. It's a one stop stop that handles many things, including environment
variables.

In our previous example, pretend for a moment we wanted to make `my_tool.py`
available to all of our Nuke Rez packages across all of supported OSes.
To do this, open

`{respawn_location}/vendors/rezzurect/adapters/nuke/nuke_setting.py`

In there is a single class called "CommonNukeSettingAdapter". Add the same
your `env.PYTHONPATH.append` command from before inside of it.


```python
class CommonNukeSettingAdapter(common_setting.BaseAdapter):

	# ... more code

    def execute(self):
        super(CommonNukeSettingAdapter, self).execute()
		env.PYTHONPATH.append('~/my_modules')
```

Now if you refresh Shotgun Desktop and load any version of Nuke, you can import
your `my_tool.py`.

Important:
	If you want to set paths in different OSes, repeat the same steps but do it
	in `nuke_setting_{OSTYPE}.py` instead. 
	(Example: Add it to `nuke_setting_windows.py` in the 
	`WindowsNukeSettingAdapter` class, instead.)

Note:
	All Rez packages that share code will follow the same folder structure.
	So if you're ever in-doubt about where to add aliases and environment
	variables, just check 

	`{respawn_location}/vendors/rezzurect/adapters/{package}/{package}_setting.py`


### Referencing Code Within The Respawn Configuration
In Shotgun, Pipeline Configurations can be hosted on-disk or on a git server
and cloned directly to the user's folder.

According to [Shotgun's Documentation](https://support.shotgunsoftware.com/hc/en-us/articles/115000067493-Integrations-Admin-Guide),
if a Pipeline Configuration is cloned, it gets added to the user's local
directory and given a name automatically.

```
OS X: ~/Library/Caches/Shotgun/<site_name>
Windows: %APPDATA%\Shotgun\<site_name>
Linux: ~/.shotgun/<site_name>
```

Like the previous example, imagine if we wanted to add `my_tool.py` directly 
into Respawn, into the Shotgun Pipeline Configuration and then add that path
to PYTHONPATH. How would we do that? Pipeline Configurations can be installed
basically anywhere so it would be difficult to define the path up-front.

The answer to this problem is to use Rezzurect.


Pretend `my_tool.py` was located here in the Pipeline Configuration:

`{tk-config-default2-respawn}/my_module/my_tool.py`

All we'd have to do is refer to the path like we did earlier in the previous
section but instead add a fancy command around it.


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

`{respawn_root}` is a special key that is defined to mean "wherever the top of
this Pipeline Configuration is". You can even define your own keys to refer to
other locations on-disk. See [Keys And Locations](TODO URL HERE) for more details.


### Linking Code From Respawn



TODO: Make a table to show when to use what append option

