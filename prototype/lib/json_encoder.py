
import json
import uuid

json_classes = {}

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        
        classname = type(obj).__name__
        t = json_classes.get(classname, None)
        if t is not None:
            d = obj.serialize()
            d['__class__'] = classname
            return d
        
        return json.JSONEncoder.default(self, obj)

def object_hook(dct):
    if '__class__' in dct:
        return json_classes[dct['__class__']].deserialize(dct)
    return dct

def register(cls):
    global json_classes
    json_classes[cls.__name__] = cls
    
