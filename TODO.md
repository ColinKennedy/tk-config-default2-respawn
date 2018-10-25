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
- Remove the need to pip install rez!!!
- Once SideFX support gets back to me about how to download Houdini 17+, add
  that to the houdini Rez packages


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

- Make sure to write a page to explain the `"{DCC}_installation"` repositories
  and why they are necessary


- Make a "How Stuff Works" section that explains why things work the way they
  do
  - explain how REZCONFIG_FILE env var is hacked to get relative pipeline
	configuration root
  - explain how `ressurect.utils.resolver` passes information to the
	executing context as environment variables
