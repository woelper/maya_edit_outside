import os
#from m2b import *
import m2b as edit_mesh
reload(edit_mesh)

#print edit_mesh
#print m2b
edit_mesh.BLENDER_SCRIPT = os.path.join(os.path.dirname(m2b.__file__),'b2m.py')
#print m2b.blender_script

#print dir(m2b)