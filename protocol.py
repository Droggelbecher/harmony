
protocols = {}

def register_protocol(p):
	global protocols
	protocols[p.name] = p
	
def find_protocol(uri):
	global protocols
	name = uri.split(':')[0]
	return protocols[name]

