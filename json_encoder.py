
import json

json_classes = set()

class JSONEncoder(json.JSONEncoder):
	def default(self, obj):
		if isinstance(obj, set):
			return list(obj)
		
		if type(obj) in json_classes:
			print(obj)
			return obj.serialize()
		
		return json.JSONEncoder.default(self, obj)

def register(cls):
	global json_classes
	json_classes.add(cls)
	
