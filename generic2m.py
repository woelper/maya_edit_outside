

import socket
import os
import sys

home = os.path.expanduser('~') 
importpath = os.path.join(home, 'Documents', 'lab', 'm2b')
#sys.path.append(importpath)

host = '127.0.0.1'
port = 6006

UUID = 'F2FCB409-9E40-CC3B-ED2B-A8BD80D9D1B3'
message = 'import sys;sys.path.append("/Users/jwoelper/Documents/lab/m2b");import m2b;m2b.update("' + UUID + '")'
message = 'import m2b;m2b.edit_mesh.update("' + UUID + '")'

#import m2b
#reload(m2b)
#m2b.edit_mesh.UiClass()


maya = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
maya.connect( (host,port) )
print maya.send(message)
maya.close()
