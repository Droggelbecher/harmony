
import os.path
from harmony import serialization
from harmony.harmony_component import FileComponent

class Remotes(FileComponent):

    RELATIVE_PATH = 'remotes'

    class Remote:
        def __init__(self, id_, name, location):
            self.id = id_
            self.name = name
            self.location = location

        @classmethod
        def from_dict(class_, d):
            return class_(**d)

        def to_dict(self):
            return {
                'id': self.id,
                'name': self.name,
                'location': self.location
            }



    def __init__(self, path, by_name = None, by_id = None):
        super().__init__(path)
        self.by_name = by_name if by_name else {}
        self.by_id = by_id if by_id else {}

    @classmethod
    def from_dict(class_, d):
        by_name = { x['name']: Remote.from_dict(x) for x in d['remotes'] }
        by_id = { x['id']: Remote.from_dict(x) for x in d['remotes'] }
        return class_(d['path'], by_name, by_id)

    def to_dict(self):
        l = list(set(self.by_name.values()) | set(self.by_id.values()))
        return {
            'remotes': l,
        }

    def add(self, location, id_, name = None):
        if name is not None:
            self.by_name[name] = location
        self.by_id[id_] = location

    def get_location_any(self, s):
        """
        Return a location by a "fuzzy" search
        (meaning s can either be a name or an ID of a location).
        """
        r = self.get_location(s, s)
        if r is None:
            return s

    def get_location(self, id_ = None, name = None):
        if id_ is not None and id_ in self.by_id:
            return self.by_id[id_]
        if name is not None and name in self.by_name:
            return self.by_name[name]
        return None

    def get_locations(self):
        s = set(self.by_name.values())
        s.update(self.by_id.values())
        return s




