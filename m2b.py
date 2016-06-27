
import sys
import os
import pymel.core as pm
import maya.cmds as cmds
import tempfile
import json
import subprocess
from PySide import QtCore  
from PySide.QtGui import *  
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin  




# /// UTILS

def unroll_list(list_):
    if type(list_) is not list:
        return list_
    if len(list_) > 0:
        return list_[0]

def is_material(node):
    has_se = False
    has_file = False
    for c in node.listConnections():
        if c.type() == 'shadingEngine':
            has_se = True
        elif c.type() == 'file':
            has_file = True
    if has_file and has_se:
        if node.type() != 'materialInfo' and node.type() != 'nodeGraphEditorInfo':
            #print node, 'is material', node.type()
            return node
    return None


def guess_diffuse_file(node):
   
    mat = [pm.ls(pm.listConnections(se), materials=True) for se in node.getShape().outputs(type='shadingEngine')][0]
    mat = unroll_list(mat)
    if mat is None:
        # use alternate approach
        candidates = [[is_material(m) for m in pm.listConnections(se)] for se in node.getShape().outputs(type='shadingEngine')][0]
        for c in candidates:
            if c is not None:
                mat = c
    
    textures = [c for c in mat.listConnections() if c.type() =='file']
    for t in textures:
        plugs = t.listConnections(plugs=True)
        if any ([p.name() for p in plugs if 'color' in p.name() or 'diff' in p.name()]):
            return t.fileTextureName.get()
    

    return 'untextured'


def get_blender_path(root='/Applications'):
    bin_location = 'Contents/MacOS/blender'
    for directory in os.listdir(root):
        full_path = os.path.join(root, directory)
        if os.path.isdir(full_path):
            if directory.endswith('blender.app'):
                return os.path.join(root, directory, bin_location)
            else:
                for subdir in os.listdir(full_path):
                    if subdir.endswith('blender.app'):
                        return os.path.join(full_path, subdir, bin_location)


def replace_mesh(old, new):
    shading_engines = old.getShape().outputs(type='shadingEngine')[0]

    old_mesh = old.listRelatives(shapes=True)[0]
    old_mesh_name = old_mesh.name()
    pm.delete(old_mesh)
    print new
    new_mesh = new.listRelatives(shapes=True)[0]
    pm.rename(new_mesh, old_mesh_name)
    pm.parent(new_mesh, old, shape=True, relative=True)
    pm.delete(new)
    
    pm.sets(shading_engines, edit=True, forceElement=old)  


def load_geofile(filepath):
    try:
        imported_nodes = pm.importFile(filepath, i=True, returnNewNodes=True)
        # print imported_nodes
    
        relevant_nodes = []
        trash = []
        for node in imported_nodes:
            print node, 'TYPE', node.type()
            if node.type() == 'mesh' or node.type() == 'transform':
                relevant_nodes.append(node)
                print '> append', node
            else:
                trash.append(str(node.name()))
                
        # seems like a bug in pymel, materials et al must be
        # explicitly deleted by string name with cmds
        for item in trash:
            try:
                cmds.delete(item)
            except ValueError:
                pass 
            
        for node in relevant_nodes:
            if node.getParent() is None:
                return node 
                
    except RuntimeError:
        print "> unreadable:", filepath
        return False



def open_port(number):
    if not cmds.commandPort(':'+str(number), q=True):
        cmds.commandPort('mayaCommand', name=':'+str(number), sourceType='python')

def get_temp_dir():
    prefix = 'm2b'
    base_tmp = tempfile.gettempdir()
    m2b_tmp = os.path.join(base_tmp, prefix)
    if not os.path.isdir(m2b_tmp):
        os.makedirs(m2b_tmp)
    return m2b_tmp
    
    
# /// CLASSES




class AppSettings(object):
    def __init__(self):
        self.conffile = os.path.join(os.path.expanduser('~'), '.maya_meshedit.conf')
        self.settings = self.load()
        if self.settings is None:
            self.gen_defaults()
            self.save()
        else:
            if len(self.settings['default_app']) > 0:
                self.set_default(self.settings['default_app'])
        
        self.app = None
        self.binary = None
        self.extensions = []    
    
    def gen_defaults(self):
        self.settings = {}
        self.settings['houdini'] = {'extensions': ['.hipnc', '.hip', '.hiplc']}
        self.settings['modo'] = {'extensions': ['.hipnc', '.hip', '.hiplc']}
        self.settings['blender'] = {'extensions': ['.blend']}
        self.settings['default_app'] = ''
        
    def set_default(self, appid):
        self.settings['default_app'] = appid
        self.app = appid
        self.extensions = self.settings[appid]['extensions']
        if 'binary' in self.settings[appid].keys():
            self.binary = self.settings[appid]['binary']
        
    def load(self):
        if os.path.isfile(self.conffile):
            with open(self.conffile) as conffile:
                return json.load(conffile)

    def save(self):
        try:
            with open(self.conffile, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except:
            print 'could not write', self.settings    
            
    def __repr__(self):
        return 'sssss'
        #return '{0}'.format(self.app self.binary, self.settings)


class AtOrigin(object):
    def __init__(self, node):
        self.node = node
        self.matrix = pm.xform(matrix=True, query=True)
    
    def __enter__(self):
        print '> discard trs'
        mat_neutral = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        pm.xform(self.node, matrix=mat_neutral)

    def __exit__(self, type, value, traceback):
        print '> restore trs'
        pm.xform(self.node, matrix=self.matrix)


class KeepSelection(object):
    def __enter__(self):
        print '> store sel'
        self.selection = pm.selected()
        
    def __exit__(self, type, value, traceback):
        print '> restore sel'
        pm.select(self.selection)

#################### GUI

class UiClass (MayaQWidgetDockableMixin, QWidget):
    def __init__(self, parent=None):
        super(UiClass, self).__init__(parent=parent)
        window_name = 'Edit externally'

        if cmds.window(window_name, q=True, ex=True):
            cmds.deleteUI(window_name)

        self.setWindowTitle(window_name)
        self.setObjectName(window_name)
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.resize(300, 300)


        def get_binary():
            binary = QFileDialog.getOpenFileName(None, 'Select executable')
            if len(binary[0]) > 1:
                return binary[0]


        def start_bridge():
            do_discard = False
            if w_check_force.isChecked():
                do_discard = True
            
            current_app_name = w_combobox.currentText()
            APP_SETTINGS.set_default(current_app_name)
            
            #print APP_SETTINGS.settings[current_app_name]
            if APP_SETTINGS.binary is None:
                print 'select binary for', current_app_name
                binary = get_binary()
                if binary is not None:
                    APP_SETTINGS.settings[current_app_name]['binary'] = binary
                    APP_SETTINGS.binary = binary
                    APP_SETTINGS.save()
                else:
                    print 'Could not get binary for', current_app_name                    
                
            init(discard=do_discard)
            self.close()
             

        layout = QVBoxLayout()
        w_combobox = QComboBox()
        w_combobox.addItem('blender')
        w_combobox.addItem('houdini')
        w_combobox.addItem('modo')
        w_check_force = QCheckBox('Discard history')
        
        w_confirm = QPushButton('Edit in app')
        w_confirm.clicked.connect(start_bridge)
        
        layout.addWidget(w_check_force)
        if APP_SETTINGS.binary is None:
            layout.addWidget(QLabel('Path to app not found. You will be \nprompted to select one.'))    
        layout.addWidget(QLabel('App to open'))
        layout.addWidget(w_combobox)
        layout.addWidget(w_confirm)
        
        self.setLayout(layout)
        self.show()

class BridgedNode(object):
    def __init__(self, uuid):
        self.uuid = uuid
        self.node = None
        self.texture = None
        self.geofile = None
        self.metadatafile = None
        self.matrix = None
        self.valid = False
        self.blendfile = False
        self.updatescript = None   
        
        self.ingest()
    
    def is_valid(self):
        print '> validating:'
        #print [ (key, self.__dict__[key]) for key in self.__dict__.keys()]
    
        if not any([self.__dict__[key] is None for key in self.__dict__.keys()]):
            print '> valid'
            return True
        else:
            print '> invalid'
            print [self.__dict__[key] for key in self.__dict__.keys()]
        
    def has_history(self):
        if os.path.isfile(self.geofile) and os.path.isfile(self.metadatafile) and os.path.isfile(self.blendfile):            
            return True 
    
    def erase_history(self):
        for f in [self.geofile, self.metadatafile, self.blendfile]:
            try:
                os.unlink(f)
            except:
                print 'Could not delete', f
    
    
    def ingest(self):
        # get scene object
        for node in pm.ls(transforms=True):
            if cmds.ls(node.name(), uuid=True)[0] == self.uuid:
                self.node = node
        self.geofile = os.path.join(get_temp_dir(), self.uuid + GEO_EXT)
        self.blendfile = os.path.join(get_temp_dir(), self.uuid + APP_EXT)
        self.metadatafile = os.path.join(get_temp_dir(), self.uuid + '.json')
        self.matrix = pm.xform(matrix=True, query=True)
        #print 'node', self.node
        self.texture = guess_diffuse_file(self.node)
        self.updatescript = BLENDER_SCRIPT
        
    def dump_metadata(self):
        metadata = {'obj': self.geofile,
            'tex': self.texture,
            'blend': self.blendfile,
            'uuid': self.uuid,
            'updatescript': self.updatescript,
            'port': PORT
            }
       
    
        #print '> metadata: ', metadata
        with open(self.metadatafile, 'w') as f:
            json.dump(metadata, f, indent=4)
            
    def dump_geo(self):
        print '> dumping mesh'
        # save position
        with AtOrigin(self.node):
            cmds.file(self.geofile,
                        force=True,
                        pr=1,
                        typ="OBJexport",
                        exportSelected=True,
                        op="groups=0;materials=0;smoothing=0;normals=1")

        
    def edit_in_app(self):
        
        binary = APP_SETTINGS.binary
        
        OSX_BLENDER_BIN = 'Contents/MacOS/blender'
        #print 'APP', APP_SETTINGS.app
        if APP_SETTINGS.app == 'blender':
            print 'blender detected'
            # OSX...
            if binary.endswith('.app'):
                binary = os.path.join(binary, OSX_BLENDER_BIN)
        
        blendfile = self.blendfile
        cmd = [binary, '--python', BLENDER_SCRIPT, blendfile]
        #print 'CMD', cmd
        subprocess.Popen(cmd)


# // SETTINGS
GEO_EXT = '.obj'
APP_EXT = '.blend'
PORT = 6006
BLENDER_SCRIPT = ''
APP_SETTINGS = AppSettings()

print 'SETTINGS', APP_SETTINGS
     
# /// CONTROLS

def init(discard=False):
    
    
    selection = pm.selected()
    if len(selection) != 1:
        print 'Must select one object'
    else:
        selection = selection[0]
        uuid = cmds.ls(selection.name(), uuid=True)[0]
        bn = BridgedNode(uuid)
        
        if discard:
            bn.erase_history()
        
        bn.ingest()
        
        if bn.is_valid():
            if bn.has_history():
                print '> file has history. opening source.'
            else:
                bn.dump_geo()
                bn.dump_metadata()
        else:
            bn.dump_geo()
            bn.dump_metadata()


        open_port(PORT)
        bn.edit_in_app()


def update(uuid):
    
    
    
    
    
    print '> running on', uuid
    bn = BridgedNode(uuid)
    bn.ingest()
    if bn.is_valid():
        with KeepSelection():
            print 'GEO', bn.geofile
            imported_node = load_geofile(bn.geofile)
            replace_mesh(bn.node, imported_node)
    else:
        print '> UUID invalid.'
                