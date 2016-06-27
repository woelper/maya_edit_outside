# Edit your meshes with your favorite app.

If you have a hard time modeling in Maya but find yourself comfortable editing in blender, this is for you.

## Features:

* Opens a single selected object in blender.
* Upon saving the blender scene, maya is signalled an update and maya will automatically display the updated mesh.
* Materials and attributes as well as rotation, transform and scaling will be retained in maya.
* The current diffuse texture will be displayed in blender.
* m2b is based on UUIDs. You can add modifiers and other stuff, quit blender and next time you click m2b the blender scene will be reopened.

## Installation:

open a terminal and navigate to your maya scipts folder, such as:

* Windows: <drive>:\Documents and Settings\<username>\My Documents\maya\<Version>\scripts
* Mac OS X: ~/Library/Preferences/Autodesk/maya/<version>/scripts
* Linux: ~/maya/<version>/scripts

git clone https://github.com/woelper/m2b.git


In Maya, drag this to a shelf button:


```python
import m2b
m2b.edit_mesh.UiClass()
```

Further reading:
https://knowledge.autodesk.com/support/maya/learn-explore/caas/CloudHelp/cloudhelp/2016/ENU/Maya/files/GUID-C0F27A50-3DD6-454C-A4D1-9E3C44B3C990-htm.html


## Limitations:
* Maya object may only have one shader.
* Only one texture is signalled to blender.

## TODO:
* Add a connection for Houdini
* Add a connection for Modo
* Make it cross-platform
* Browse for blender location

## Misc:
* By now, data is exchanged via OBJ. All limitations of OBJ apply.
