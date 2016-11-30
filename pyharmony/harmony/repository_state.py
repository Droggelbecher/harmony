
import logging
from copy import deepcopy

from harmony.harmony_component import FileComponent
from harmony.clock import Clock
from harmony import serialization

logger = logging.getLogger(__name__)

class Entry:
    def __init__(self, path = None, digest = None, clock = Clock()):
        self.digest = digest
        self.path = path
        self.clock = clock

    @classmethod
    def from_dict(class_, d):
        e = class_()
        e.digest = d['digest']
        e.path = d['path']
        e.clock = Clock.from_dict(d['clock'])
        return e

    def to_dict(self):
        return {
            'digest': self.digest,
            'path': self.path,
            'clock': self.clock.to_dict(),
        }

    def contents_different(self, other):
        return self.digest != other.digest

    def __repr__(self):
        return 'Entry(path={!r}, digest={!r}, clock={!r})'.format(
            self.path, self.digest, self.clock
        )

class RepositoryState(FileComponent):

    RELATIVE_PATH = 'repository_state'

    def __init__(self, path, files = None):
        super().__init__(path)
        self.files = files if files else {}

    @classmethod
    def from_dict(class_, d):
        return class_(
            d['path'],
            files = {
                f: Entry.from_dict(v)
                for f, v in d['files'].items()
            }
        )

    def to_dict(self):
        return {
            'files': {
                f: v.to_dict()
                for f, v in self.files.items()
            }
        }

    def get_paths(self):
        return self.files.keys()

    # TODO: turn get_entry/set_entry into item access

    def get_entry(self, path):
        return deepcopy(self.files.get(path, Entry(path = path)))

    def set_entry(self, path, entry):
        logger.debug('---- set_entry {} {}'.format(path, entry))
        self.files[path] = entry

    def overwrite(self, other):
        logger.debug('---- overwriting repo state with {}'.format(other.files))
        self.files = deepcopy(other.files)

    def update_file_state(self, new_state, id_, clock_value):
        logger.debug('---- update file state {} {} {}'.format(new_state.path,
                                                              id_, clock_value))
        #logger.debug('[{}] = {}
        path = new_state.path
        entry = self.get_entry(path)

        if new_state.digest == entry.digest:
            # Nothing changed, really, no need to update anything.
            return

        entry.digest = new_state.digest
        entry.clock.values[id_] = clock_value
        self.set_entry(path, entry)
