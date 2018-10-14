- Get it to work with FTP
- Get it to work with Houdini
- Get it to work with Nuke
 - Confirm link
 - Confirm internet
- Figure out deployment


- Right now the Nuke package gets a "install" folder built, even though it
  doesn't use it. Remove it


- Also figure out how to add rez (the python package). Very important obviously

- Make sure that Nuke depends upon (and installs) libGLU
 - Otherwise this happens: "Failed to load libstudio-11.2.3.so: libGLU.so.1: cannot open shared object file: No such file or directory"

Include Rez as part of the rez packages (so that we make sure that Rez is installed).



Build Steps
--- Attempt to get the package configuration
- If the context could not resolve then
 --- Load the package.py file directly in the original environment location
 - Iterate over the required packages (recursively)
  -? (maybe through the package?)
 - Build each package as-needed
