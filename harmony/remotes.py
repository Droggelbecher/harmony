
import os.path
from harmony import serialization
from harmony.serialization import FileSerializable, Serializable

class Remotes(FileSerializable):

    RELATIVE_PATH = 'remotes'

    class Remote(Serializable):
        """
        Represents a remote Location.
        """

        def __init__(self, id=None, name=None, location=None):
            self.id = id
            self.name = name
            self.location = str(location)

        def __eq__(self, other):
            return self.id == other.id \
                    and self.name == other.name \
                    and self.location == other.location

        def __lt__(self, other):
            return self.id < other.id \
                    or self.name < other.name \
                    or self.location < other.location

        def __hash__(self):
            return hash(self.id) \
                    ^ hash(self.name) \
                    ^ hash(self.location)


    def __init__(self, path, by_name=None, by_id=None):
        super().__init__(path)
        self.by_name = by_name if by_name else {}
        self.by_id = by_id if by_id else {}

    @classmethod
    def from_dict(class_, d):
        by_name = {x['name']: class_.Remote.from_dict(x) for x in d['remotes']}
        by_id = {x['id']: class_.Remote.from_dict(x) for x in d['remotes']}
        return class_(d['path'], by_name, by_id)

    def to_dict(self):
        l = self.get_remotes()
        return {
            'remotes': sorted(
                [x.to_dict() for x in l],
                key=lambda d: (d['name'], d['id'], d['location'])
            ),
        }

    def add(self, location, name, id=None):
        if name in self.by_name:
            raise ValueError('Remote with name "{name}" already exists.')

        if id is not None and id in self.by_id:
            raise ValueError(f'Remote with ID "{id}" already exists.')

        self.by_name[name] = self.Remote(id=id, name=name, location=location)
        if id is not None:
            self.by_id[id] = self.Remote(id=id, name=name, location=location)

    def get_location_any(self, s: str) -> str:
        """
        Return a location by a "fuzzy" search
        (meaning s can either be a name or an ID of a location).
        """
        r = self.get_location(s, s)
        if r is None:
            return s
        return r

    def get_location(self, id=None, name=None):
        if id is not None and id in self.by_id:
            return self.by_id[id].location
        if name is not None and name in self.by_name:
            return self.by_name[name].location
        return None

    def get_remotes(self):
        return list(set(self.by_name.values()) | set(self.by_id.values()))


