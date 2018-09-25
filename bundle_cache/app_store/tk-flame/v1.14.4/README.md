## Documentation
This repository is a part of the Shotgun Pipeline Toolkit.

- For more information about this app and for release notes, *see the wiki section*.
- For general information and documentation, click here: https://support.shotgunsoftware.com/entries/95441257
- For information about Shotgun in general, click here: http://www.shotgunsoftware.com/toolkit

## Using this app in your Setup
All the apps that are part of our standard app suite are pushed to our App Store.
This is where you typically go if you want to install an app into a project you are
working on. For an overview of all the Apps and Engines in the Toolkit App Store,
click here: https://support.shotgunsoftware.com/entries/95441247.

## Have a Question?
Don't hesitate to contact us! You can find us on support@shotgunsoftware.com

## Flame Engine Logging
The Flame engine logs information to `/usr/discreet/log/tk-flame.log`. This is helpful if you are trying
to troubleshoot or debug.

## Flame Engine Bootstrap
The Flame engine uses a more complex bootstrap than most other engines
and it runs in three different states - before Flame launches, during Flame operation,
and as part of backburner jobs.

For details around the bootstrap, see comments in individual files. Below is a summary of how
Flame is typically being launched:

- The multi launch app (or equivalent) reaches into `python/startup/bootstrap.py` and passes DCC launch paths
  and arguments. This method tweaks library paths and a few other minor things and returns a
  set of *rewritten* paths, where the main launch binary now is a script inside the flame engine.
  For example, the multi launch app may pass the following parameters into the bootstrap script:

  ```
  app_path: /usr/discreet/flame_2015.2/bin/startApplication
  app_args: --extra args
  ```

  The bootstrap script then returns the following:

  ```
  app_path: /usr/discreet/Python-2.6.9/bin/python
  app_args: /mnt/software/shotgun/my_project/install/engines/app-store/tk-flame/v1.2.3/startup/launch_app.py
            /usr/discreet/flame_2015.2/bin/startApplication
            --extra args
  ```

- The multi launch app now executes the re-written DCC path and thereby starts executing `python/startup/launch_app.py`.
  inside the python interpreter which comes bundled with Flame (and contains a known version of PySide). The engine starts
  up, hooks paths are registered by setting the `DL_PYTHON_HOOK_PATH` environment variable etc.
  At this point, a check is carried out to see if a Flame project corresponding to the Shotgun project exists or not.
  If it doesn't, a project setup UI is shown on screen where a user can configure a new Flame project.

- Once a Project has been established, the Flame DCC is launched.
