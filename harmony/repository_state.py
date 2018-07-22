
import logging
from copy import deepcopy
from pathlib import Path
from collections import ChainMap
from typing import Iterable

from harmony.serialization import FileSerializable, Serializable
from harmony.clock import Clock
from harmony import serialization

logger = logging.getLogger(__name__)

class RepositoryStateException(Exception):
    pass

class RepositoryFileState(Serializable):

    """
    A RepositoryFileState represents one of possibly many known
    states of a file from the point of view of the whole repository,
    that is, (amongst other things), its digest and clock.  It does
    specifically not contain any information about availability on
    particular locations or its state in the filesystem at those,
    which is handled by working_directory.FileState.
    """

    def __init__(self, path = None, digest = None, clock = Clock(), wipe = False):
        self.digest = digest
        self.path = Path(path) if path is not None else None
        self.clock = clock
        self.wipe = wipe

    @classmethod
    def from_dict(class_, d):
        d = ChainMap({ 'clock': Clock(**d['clock']) }, d)
        r = super().from_dict(d)
        return r

    def contents_different(self, other):
        return self.digest != other.digest

    def __repr__(self):
        return str(self.__dict__)

class RepositoryState(FileSerializable):

    RELATIVE_PATH = 'repository_state'

    def __init__(self, path, files = None):
        super().__init__(path)
        self.files = files if files else {}

    @classmethod
    def from_dict(class_, d):
        return class_(
            d['path'],
            files = {
                f: RepositoryFileState.from_dict(v)
                for f, v in d['files'].items()
            }
        )

    def get_paths(self) -> Iterable[Path]:
        return tuple(Path(p) for p in self.files.keys())

    def get(self, path : Path, default = None):
        return self.files.get(str(path), default)

    def __getitem__(self, path):
        return deepcopy(self.files.get(str(path), RepositoryFileState(path = path)))

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

