
import datetime
from copy import deepcopy
import logging

from harmony import serialization
from harmony.file_state import FileState
from harmony.harmony_component import DirectoryComponent
from harmony.util import datetime_to_iso, iso_to_datetime

logger = logging.getLogger(__name__)

class LocationStates(DirectoryComponent):

    RELATIVE_PATH = 'location_states'

    def __init__(self, path):
        super().__init__(path)

    @staticmethod
    def now():
        return datetime_to_iso(datetime.datetime.now())


    def get_clock(self, id_):
        return self.state[id_]['clock']

    def write_item(self, data, path):
        modified = data.get('modified', False)
        if modified:
            data['clock'] += 1

        logging.debug('Location {} was {}modified clock={}'.format(
            data['location'],
            'not ' if not modified else '',
            data['clock']
        ))
        d = {
            'location': data['location'],
            'clock': data['clock'],
            'last_modification': data['last_modification'],
            'files': {
                k: v.to_dict()
                for k, v in data['files'].items()
            },
        }
        data['modified'] = False
        serialization.write(d, path)

    def read_item(self, path):
        data = serialization.read(path)
        data['files'] = {k: FileState.from_dict(v) for k, v in data['files'].items()}
        return data

    def get_file_state(self, id_, path):
        r = self.state.get(id_, { 'files': {} })['files'].get(path, FileState(path=path))
        #logger.debug('get_file_state({}, {}) = {}'.format(
            #id_, path, r
        #))
        return r

    def get_all_paths(self, id_ = None):
        if id_ is None:
            r = set()
            for d in self.state.values():
                r.update(set(d['files'].keys()))
            return r

        else:
            return self.state[id_]['files'].keys() if id_ in self.state else ()

    def get_locations(self):
        return self.state.keys()

    def iterate_file_states(self, id_):
        return self.state.get(id_, { 'files': {} })['files'].values()


    def update(self, other):
        logger.debug('location_states update')
        for id_, d in other.state.items():
            if id_ not in self.state or self.state[id_]['clock'] < d['clock']:
                logger.debug('overwriting state for {} with remote'.format(id_))
                self.state[id_] = deepcopy(d)
            else:
                logger.debug('keeping state for {}'.format(id_))
                logger.debug('  clock local:  {} t={}'.format(self.state[id_]['clock'], self.state[id_]['last_modification']))
                logger.debug('    {}'.format(self.state[id_]['files']))
                logger.debug('  clock remote: {} t={}'.format(d['clock'], d['last_modification']))
                logger.debug('    {}'.format(d['files']))

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
        #assert file_state.clock == file_state_.clock
        assert file_state.digest == file_state_.digest

        if id_ not in self.state:
            self.state[id_] = {
                'last_modification': self.now(),
                'location': id_,
                'files': {},
                'clock': 0,
            }

        p = file_state.path
        files = self.state[id_]['files']
        if p not in files or file_state.contents_different(files[p]):
            files[p] = file_state
            self.state[id_]['modified'] = True
            self.state[id_]['last_modification'] = self.now()
            return True

        return False


    def was_modified(self, id_):
        return self.state[id_]['modified']

