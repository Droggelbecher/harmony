
import logging
from copy import deepcopy
from pathlib import Path

from harmony.harmony_component import FileComponent
from harmony.clock import Clock
from harmony import serialization

logger = logging.getLogger(__name__)

# TODO: Make more consistent with FileState
class Entry:
    def __init__(self, path = None, digest = None, clock = Clock(), wipe = False):
        self.digest = digest
        self.path = Path(path) if path is not None else None
        self.clock = clock
        self.wipe = wipe

    @classmethod
    def from_dict(class_, d):
        e = class_()
        e.digest = d['digest']
        e.path = Path(d['path'])
        e.clock = Clock.from_dict(d['clock'])
        e.wipe = d['wipe']
        return e

    def to_dict(self):
        return {
            'digest': self.digest,
            'path': str(self.path),
            'clock': self.clock.to_dict(),
            'wipe': self.wipe,
        }

    def contents_different(self, other):
        return self.digest != other.digest

    def __repr__(self):
        return str(self.__dict__)

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
                str(f): v.to_dict()
                for f, v in self.files.items()
            }
        }

    def get_paths(self):
        return self.files.keys()

    def get(self, path, default = None):
        return self.files.get(path, default)

    def __getitem__(self, path):
        return deepcopy(self.files.get(str(path), Entry(path = path)))

    def __setitem__(self, path, v):
        self.files[str(path)] = v

    def overwrite(self, other):
        self.files = deepcopy(other.files)

    def update_file_state(self, new_state, id_, clock_value):
        path = new_state.path
        entry = deepcopy(self[str(path)])

        if new_state.digest == entry.digest and new_state.wipe == entry.wipe:
            # Nothing changed, really, no need to update anything.
            return

        entry.wipe = new_state.wipe
        entry.digest = new_state.digest
        entry.clock.values[id_] = clock_value
        self[path] = entry

