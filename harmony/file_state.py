
import logging
import os
from copy import deepcopy
from pathlib import Path

logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)

class FileState:
    """
    Represents a recorded file's state (hash value, size, etc...).
    Generated in WorkingDirectory, stored in LocationState.
    """
    # TODO: Possibly move this into WorkingDirectory, make consistent with location_state.Entry

    def __init__(self, path = None, digest = None, size = None, mtime = None,
                 wipe = False):
        self.path = Path(path)
        self.digest = digest
        self.size = size
        self.mtime = mtime
        self.wipe = wipe

    def __deepcopy__(self, memo):
        return FileState(
            self.path,
            self.digest,
            self.size,
            self.mtime,
            self.wipe,
        )

    @classmethod
    def from_dict(class_, d):
        return class_(**d)

    def to_dict(self):
        return {
            'path': str(self.path),
            'digest': self.digest,
            'size': self.size,
            'mtime': self.mtime,
            'wipe': self.wipe,
        }

    def exists(self):
        return self.size is not None

    def contents_different(self, other):
        return self.size != other.size or self.digest != other.digest


