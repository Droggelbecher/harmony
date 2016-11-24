
import datetime
from harmony.util import datetime_to_iso, iso_to_datetime
from harmony import serialization
from harmony.file_state import FileState
from harmony.harmony_component import DirectoryComponent

class LocationState(DirectoryComponent):

    RELATIVE_PATH = 'history'

    def __init__(self, path):
        super().__init__(path)

    def create_state(self, location_id):
        if location_id not in self.state:
            self.state[location_id] = {
                'location': location_id,
                'files': {},
                'modified': True
            }

    def write_item(self, obj, path):
        data = obj
        d = {
            'location': data['location'],
            'last_modification': datetime_to_iso(datetime.datetime.now())
                if data.get('modified', False) else data['last_modification'],
            'files': {
                k: {
                    'path': v.path,
                    'digest': v.digest,
                    'size': v.size,
                    'mtime': v.mtime,
                    'clock': v.clock,
                } for k, v in data['files'].items()
            },
        }
        serialization.write(d, path)

    def read_item(self, path):
        data = serialization.read(path)
        data['files'] = {kws['path']: FileState(**kws) for kws in data['files'].values()}
        return data

    def get_file_state(self, id_, path):
        return self.state.get(id_, { 'files': {} })['files'].get(path, None)

    def get_all_paths(self):
        r = set()
        for d in self.state.values():
            r.update(set(d['files'].keys()))
        return r

    def get_locations(self):
        return self.state.keys()

    def iterate_file_states(self, id_):
        return self.state.get(id_, { 'files': {} })['files'].values()

    def update_file_state(self, id_, file_state):

        # TODO: Clocks!!!
        # TODO: Also look into other locations for this file to get clock
        # values if its not in local location
        #
        p = file_state.path
        files = self.state[id_]['files']
        if p not in files or file_state.contents_different(files[p]):
            files[p] = file_state
            self.state[id_]['modified'] = True

    def was_modified(self, id_):
        return self.state[id_]['modified']

