
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

    def write_item(self, data, path):
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
                } for k, v in data['files'].items()
            },
        }
        serialization.write(d, path)

    def read_item(self, path):
        data = serialization.read(path)
        data['files'] = {kws['path']: FileState(**kws) for kws in data['files'].values()}
        return data

    def iterate_file_states(self, id_):
        return self.state[id_]['files'].values()

    def update_file_state(self, id_, file_state):
        # TODO: Clocks!!!
        #
        p = file_state.path
        files = self.state[id_]['files']
        if p not in files or file_state.contents_different(files[p]):
            files[p] = file_state
            self.state[id_]['modified'] = True

    def was_modified(self, id_):
        return self.state[id_]['modified']

