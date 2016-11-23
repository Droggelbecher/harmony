
import datetime
from harmony.util import datetime_to_iso, iso_to_datetime
from harmony import serialization
from harmony.file_state import FileState

class LocationState:

    @classmethod
    def load(class_, path):
        data = serialization.read(path)
        r = class_(data['location'])
        r.last_modification = data['last_modification']

        # TODO: normalize kws['path'] on loading
        r.files = {kws['path']: FileState(**kws) for kws in data['files'].values()}

    def __init__(self, location):
        self.location = location
        self.files = {}
        self.modified = False

    def write(self, path):
        d = {
            'location': self.location,
            'last_modification': datetime_to_iso(datetime.datetime.now()) if self.modified else self.last_modification,
            'files': {
                k: {
                    'path': v.path,
                    'digest': v.digest,
                    'size': v.size,
                    'mtime': v.mtime,
                } for k, v in self.files.items()
            },
        }
        serialization.write(d, path)

    def iterate_file_states(self):
        return self.files

    def update_file_state(self, file_state):
        # TODO: Clocks!!!
        #
        p = file_state.path
        if p not in self.files or file_state.contents_different(self.files[p]):
            self.files[p] = file_state
            self.modified = True

