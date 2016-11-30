
import os.path
from harmony import serialization
from harmony.harmony_component import FileComponent

class Remotes(FileComponent):

    RELATIVE_PATH = 'remotes'

    def __init__(self, path, by_name = None, by_id = None):
        super().__init__(path)
        # TODO: we can do the indexing on loading, don't save duplicate
        # information to file
        self.by_name = by_name if by_name else {}
        self.by_id = by_id if by_id else {}
        #self.state = {
            #'by_name': {},
            #'by_id': {}
        #}

    def to_dict(self):
        return {
            'by_name': self.by_name,
            'by_id': self.by_id,
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
            return selfby_id[id_]
        if name is not None and name in self.by_name:
            return self.by_name[name]
        return None
        #raise Exception('Location (id={}, name={}) not found.'
                        #.format(id_, name))

    def get_locations(self):
        s = set(self.by_name.values())
        s.update(self.by_id.values())
        return s




