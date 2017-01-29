
import datetime
from copy import deepcopy
import logging
from pathlib import Path

from harmony.working_directory import FileState
from harmony.serialization import Serializable, DirectorySerializable
from harmony.util import datetime_to_iso, iso_to_datetime, shortened_id

logger = logging.getLogger(__name__)

class LocationState(Serializable):

    _state = (
        'files',
        'clock',
        'last_modification',
        'location',
        )

    def __init__(self, files = None, clock = None, last_modification = None,
                 modified = False, location = None):
        self.files = files if files else {}
        self.clock = clock if clock else 0
        self.last_modification = last_modification
        self.modified = modified
        self.location = location

    @classmethod
    def from_dict(class_, d):
        r = super().from_dict(d)
        r.files = {
            Path(k): FileState.from_dict(v)
            for k, v in r.files.items()
        }
        return r


class LocationStates(DirectorySerializable):

    RELATIVE_PATH = 'location_states'
    Item = LocationState

    @staticmethod
    def now():
        return datetime_to_iso(datetime.datetime.now())

    def __init__(self, path, items = None):
        super(LocationStates, self).__init__(path, items if items else {})
        assert not items or type(list(items.values())[0]) is not dict

    def get_clock(self, id_):
        return self.items[id_].clock

    def item_to_dict(self, item):
        if item.modified:
            item.clock += 1
        r = super().item_to_dict(item)
        item.modified = False
        return r

    def get_file_state(self, id_, path):
        """
        preconditions:
            $path is normalized with WorkingDirectory.normalize
        """
        path = Path(path)

        r = self.items.get(id_, LocationState()).files.get(
            path,
            FileState(path = path)
        )
        return r

    def get_all_paths(self, id_ = None):
        if id_ is None:
            r = set()
            for d in self.items.values():
                r.update(set(d['files'].keys()))
            return r

        else:
            return self.items[id_].files.keys() if id_ in self.items else ()

    def get_locations(self):
        return self.items.keys()

    def iterate_file_states(self, id_):
        return self.items.get(id_, LocationState()).files.values()


    def update(self, other):
        logger.debug('location_states update')
        for id_, d in other.items.items():
            assert isinstance(d, LocationState)

            if id_ not in self.items or self.items[id_].clock < d.clock:
                logger.debug('overwriting state for {} (={}) with remote'.format(shortened_id(id_), id_))
                self.items[id_] = deepcopy(d)
            else:
                logger.debug('keeping state for {}'.format(id_))
                logger.debug('  clock local:  {} t={}'.format(self.items[id_].clock, self.items[id_].last_modification))
                logger.debug('    {}'.format(self.items[id_].files))
                logger.debug('  clock remote: {} t={}'.format(d.clock, d.last_modification))
                logger.debug('    {}'.format(d.files))

    def update_file_state(self, id_, file_state_):
        file_state = deepcopy(file_state_)

        assert file_state.path == file_state_.path
        assert file_state.digest == file_state_.digest

        if id_ not in self.items:
            self.items[id_] = LocationState(last_modification = self.now(), location = id_)

        p = file_state.path
        files = self.items[id_].files
        if p not in files or file_state.contents_different(files[p]):
            files[p] = file_state
            self.items[id_].modified = True
            self.items[id_].last_modification = self.now()
            return True

        return False


    def was_modified(self, id_):
        return self.items[id_].modified

