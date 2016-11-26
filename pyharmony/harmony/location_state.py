
import datetime
from copy import deepcopy
import logging

from harmony.util import datetime_to_iso, iso_to_datetime
from harmony import serialization
from harmony.file_state import FileState
from harmony.harmony_component import DirectoryComponent

logger = logging.getLogger(__name__)

class LocationState(DirectoryComponent):

    RELATIVE_PATH = 'history'

    def __init__(self, path):
        super().__init__(path)

    @staticmethod
    def now():
        return datetime_to_iso(datetime.datetime.now())

    def create_state(self, location_id):
        if location_id not in self.state:
            self.state[location_id] = {
                'location': location_id,
                'clock': 0,
                'files': {},
                'modified': False,
            }

    def increment_clock(self, id_):
        self.state[id_]['clock'] += 1

    def write_item(self, data, path):
        modified = data.get('modified', False)
        d = {
            'location': data['location'],
            'last_modification': data['last_modification'],
            'clock': data['clock'] + 1 if modified else data['clock'],
            #'last_modification': datetime_to_iso(datetime.datetime.now())
                #if modified else data['last_modification'],
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
        r = self.state.get(id_, { 'files': {} })['files'].get(path, FileState(path=path))
        logger.debug('get_file_state({}, {}) = {}'.format(
            id_, path, r
        ))
        return r

    def get_all_paths(self, id_ = None):
        if id_ is None:
            r = set()
            for d in self.state.values():
                r.update(set(d['files'].keys()))
            return r

        else:
            return self.state[id_]['files'].keys()

    def get_locations(self):
        return self.state.keys()

    def iterate_file_states(self, id_):
        return self.state.get(id_, { 'files': {} })['files'].values()

    def get_latest_file_state(self, path):
        """
        Requires that this history for the requested path is conflict-free.
        """
        states = [
            d['files'][path]
            for d in self.state.values()
            if path in d['files']
        ]
        heads = FileState.get_heads(states)
        assert len(heads) <= 1, 'History for {} not conflict-free.'.format(path)

        if len(heads) == 0:
            # Nobody has an entry for this file, return the trivial file_state
            # equivalent to set the VC to (0, 0, ...)
            return FileState(path = path)

        else:
            return tuple(heads)[0]


    def update(self, other):
        logger.debug('location_state update')
        for id_, d in other.state.items():
            if id_ not in self.state or self.state[id_]['clock'] < d['clock']:
                logger.debug('overwriting state for {} with remote'.format(id_))
                self.state[id_] = deepcopy(d)
            else:
                logger.debug('keeping state for {}'.format(id_))
                logger.debug('  clock local:  {} t={}'.format(self.state[id_]['clock'], self.state[id_]['last_modification']))
                logger.debug('  clock remote: {} t={}'.format(d['clock'], d['last_modification']))

                # Intentionally only setting ['modified'], but keeping the
                # last_modification date as it was so file will be written and
                # (assuming completely equal and deterministic serialization)
                # be identical to original source file
                # (which is not required but illustrates that we really didnt
                # do anything to that data)
                # EDIT: will be written anyway
                #self.state[id_]['modified'] = True

    def update_file_state(self, id_, file_state_):
        file_state = deepcopy(file_state_)

        assert file_state.path == file_state_.path
        assert file_state.clock == file_state_.clock
        assert file_state.digest == file_state_.digest

        if id_ not in self.state:
            self.state[id_] = {
                'last_modification': self.now(),
                'clock': 0,
                'location': id_,
                'files': {},
            }

        # TODO: Clocks!!!
        # TODO: Also look into other locations for this file to get clock
        # values if its not in local location
        #
        p = file_state.path
        files = self.state[id_]['files']
        if p not in files or file_state.contents_different(files[p]):
            file_state.clock[id_] = self.state[id_]['clock'] + 1
            files[p] = file_state
            self.state[id_]['modified'] = True
            self.state[id_]['last_modification'] = self.now()

    def was_modified(self, id_):
        return self.state[id_]['modified']

