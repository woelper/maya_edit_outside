
import bpy
import socket
import os
import sys
import json
from bpy.app.handlers import persistent


print('\n\n\n\n\n======================== INIT BLENDER SESSION ============================')

home = os.path.expanduser('~') 
includepath = os.path.join(home, 'Documents', 'lab', 'm2b')


# /// SETTINGS
OBJ_FILE = ''


# disable splash
bpy.context.user_preferences.view.show_splash = False


def get_sceneinfo():
    """Check if last argument is a file
    """
    arg = sys.argv[-1]
    print('> CMD LINE ARG:', arg)
    if 'blend' in arg:
        basepath = os.path.dirname(arg)
        uuid = os.path.basename(arg)
        uuid = os.path.splitext(uuid)[0]
        jsonfile = os.path.join(basepath, uuid + '.json')
        with open(jsonfile) as conffile:
            conf_data = json.load(conffile)
        print(conf_data)
        return conf_data
    
    elif 'json' in arg:
        with open(arg) as conffile:
            conf_data = json.load(conffile)
        return conf_data




def import_obj(fp):
    old_state = list(bpy.context.scene.objects)
    bpy.ops.import_scene.obj(filepath=fp)
    new_state = list(bpy.context.scene.objects)
    return set(new_state) - set(old_state)


def setup_scene():
    print('> SETTING UP SCENE')

    print('> texture:', TEXTURE)
    for object in bpy.data.objects:
        if object.name == 'Cube':
            object.select = True
            bpy.ops.object.delete()

    new_items = import_obj(OBJ_FILE)
    for object in bpy.context.scene.objects:
        object.select = False

    scn = bpy.context.scene
    scn.render.engine = 'CYCLES'
    
    mat = bpy.data.materials.new('MayaTexture')
    mat.use_nodes = True
    texnode = mat.node_tree.nodes.new(type="ShaderNodeTexImage")
    mat.node_tree.links.new(texnode.outputs['Color'], mat.node_tree.nodes['Diffuse BSDF'].inputs['Color'])
    if os.path.isfile(str(TEXTURE)):
        texnode.image = bpy.data.images.load(TEXTURE)

    for item in new_items:
        if item.type == 'MESH':
            ob = item
            mesh = ob.data
            mesh.materials.append(mat)
            item.select = True
            bpy.context.scene.objects.active = item

    
    preview_texture(TEXTURE)

    print('SAVING AS', BLEND)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND, check_existing=False)


def update_maya():
    print('MSG > MAYA', PORT)
    host = '127.0.0.1'
    port = PORT
    #message = 'import sys;sys.path.append("' + includepath + '");import m2b;m2b.update("' + UUID + '")'
    message = 'import m2b;m2b.edit_mesh.update("' + UUID + '")'
    
    maya = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    maya.connect((host, port))
    msg = bytes(message, 'UTF-8')
    try:
        print('sending')
        maya.send(msg)
    except:
        print('failed')
        print(msg)
    finally:
        print('closed')
        maya.close()

def deselect():
    for object in bpy.context.scene.objects:
        object.select = False

def preview_texture(image):
    print('> PREVIEW TEXTURE GENERATION', TEXTURE)

    for area in bpy.data.screens['Default'].areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.viewport_shade = 'TEXTURED'
                    space.show_textured_solid = True
    deselect()
    #mat = bpy.data.materials.new('TexMat')


def export():
    selection = bpy.context.selected_objects

    deselect()

    for object in bpy.context.scene.objects:
        if not object.hide_render:
            object.select = True
    bpy.ops.export_scene.obj(filepath=OBJ_FILE,
                             use_materials=False,
                             use_blen_objects=False,
                             use_selection=True)

    # restore selection
    for object in bpy.context.scene.objects:
        object.select = False
        if object in selection:
            object.select = True

    update_maya()

@persistent
def save_handler(dummy):
    export()


class BlenderBridge(object):
    def __init__(self):
        self.handler = save_handler


info = get_sceneinfo()
if info is not None:
    OBJ_FILE = info['obj']
    TEXTURE = info['tex']
    BLEND = info['blend']
    UUID = info['uuid']
    PORT = info['port']

if os.path.isfile(BLEND):
    print('> matching blend file found. using that.')
else:
    setup_scene()





if len(bpy.app.handlers.save_post) < 1:
    bpy.app.handlers.save_post.append(save_handler)
