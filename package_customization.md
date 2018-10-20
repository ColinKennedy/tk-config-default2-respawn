## A Quick Explanation About Respawn's Rez Packages
When you load Shotgun Desktop in Respawn for the first time, you'll notice that
several software packages and versions are provided by default.

Shotgun's default Pipeline Configuration, tk-config-default2, is written to
search for installed software on the user's machine and show them 
as available options. Respawn works the same way but, instead of searching for 
installed software, Respawn searches for packages found in the 
`{respawn_location}/rez_packages` folder. That way we know that anything the user 
clicks on will be controlled and managed by a Rez package, under the hood.

Any folder that contains the following structure

`{respawn_location}/rez_packages/{package_name}/{package_version}/package.py`
will be picked up as an available Rez package.


## Displaying And Filtering Rez Packages In Shotgun And Shotgun Desktop
Basically Respawn uses Shotgun Entities to decide what software and how to
display them exactly the way that Shotgun intended. All regular administrator
knowledge on Shotgun applies here.

You can filter out specific products and versions exactly the same way on
your Shotgun site's Software Entity page as you normally would and Respawn will
pick up your settings.

See the [Configuring the software in Shotgun Desktop](https://support.shotgunsoftware.com/hc/en-us/articles/115000067493#Configuring%20the%20software%20in%20Shotgun%20Desktop)
page for information on how to do this.
