
import os.path
from harmony import serialization


class Remotes:

    @classmethod
    def init(class_, harmony_directory):
        r = class_(harmony_directory)
        r.write()
        return r
    
    @classmethod
    def load(class_, harmony_directory):
        r = class_(harmony_directory)
        data = serialization.read(r.remotes_path)

        r.by_name = data['by_name']
        r.by_id = data['by_id']
        return r


    def __init__(self, harmony_directory):
        self.by_name = {}
        self.by_id = {}
        self.remotes_path = os.path.join(harmony_directory, 'remotes')

    def add(self, location, id_, name = None):
        if name is not None:
            self.by_name[name] = location
        self.by_id[id_] = location

    def write(self):
        d = {
                'by_name': self.by_name,
                'by_id': self.by_id
                }
        serialization.write(d, self.remotes_path)

    def get_location(self, id_ = None, name = None):
        if id_ is not None and id_ in self.by_id:
            return self.by_id[id_]
        if name is not None and name in self.by_id:
            return self.by_name[name]
        return None

    def get_locations(self):
        s = set(self.by_name.values())
        s.update(self.by_id.values())
        return s




