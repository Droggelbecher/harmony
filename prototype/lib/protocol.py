
import re

DEFAULT_PROTOCOL = 'file'

protocols = {}

def split_uri(uri):
    m = re.match(r'([a-zA-Z0-9]+):(.*)', uri)
    if m is not None:
        name, path = m.groups()
    else:
        name = DEFAULT_PROTOCOL
        path = uri
    return name, path
    

def register_protocol(p):
    global protocols
    protocols[p.name] = p
    
def find_protocol(uri):
    global protocols
    return protocols[split_uri(uri)[0]]

