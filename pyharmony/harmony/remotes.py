
import os.path
from harmony import serialization
from harmony.harmony_component import FileComponent

class Remotes(FileComponent):

    RELATIVE_PATH = 'remotes'

    def __init__(self, path):
        super().__init__(path)
        self.state = {
            'by_name': {},
            'by_id': {}
        }

    def add(self, location, id_, name = None):
        if name is not None:
            self.state['by_name'][name] = location
        self.state['by_id'][id_] = location

    def get_location_any(self, s):
        """
        Return a location by a "fuzzy" search
        (meaning s can either be a name or an ID of a location).
        """
        r = self.get_location(s, s)
        if r is None:
            return s

    def get_location(self, id_ = None, name = None):
        if id_ is not None and id_ in self.state['by_id']:
            return self.state['by_id'][id_]
        if name is not None and name in self.state['by_name']:
            return self.state['by_name'][name]
        return None
        #raise Exception('Location (id={}, name={}) not found.'
                        #.format(id_, name))

    def get_locations(self):
        s = set(self.state['by_name'].values())
        s.update(self.state['by_id'].values())
        return s




