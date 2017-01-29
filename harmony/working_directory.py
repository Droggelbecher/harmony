
import os
import logging
from pathlib import Path

from harmony import hashers
from harmony.serialization import Serializable

logger = logging.getLogger(__name__)

class FileState(Serializable):
    """
    Represents a recorded file's state (hash value, size, etc...).
    Generated in WorkingDirectory, stored in LocationState.
    """

    def __init__(self, path = None, digest = None, size = None, mtime = None, wipe = False):
        self.path = Path(path)
        self.digest = digest
        self.size = size
        self.mtime = mtime
        self.wipe = wipe

    def __deepcopy__(self, memo):
        return self.__class__(
            self.path,
            self.digest,
            self.size,
            self.mtime,
            self.wipe,
        )

    def exists(self):
        return self.size is not None

    def contents_different(self, other):
        return self.size != other.size or self.digest != other.digest

class WorkingDirectory:

    def __init__(self, path, ruleset):
        self.path = Path(path).resolve()
        self.ruleset = ruleset

    def normalize(self, relpath):
        abspath = (self.path / relpath)
        try:
            abspath = abspath.resolve()
        except FileNotFoundError:
            pass
        return abspath.relative_to(self.path)

    def get_filenames(self):
        r = set()
        for file_info in self.ruleset.iterate_committable_files(self.path):
            r.add(self.normalize(file_info.relative_filename))
        return r

    def __contains__(self, path):
        return (self.path / self.normalize(path)).exists()

    def file_maybe_modified(self, file_state):
        """
        Return True if the file $file_info.path suggests that it might have
        been modified since file_info was generated.

        Uses file properties such as:
            - Last modification time
            - File size

        Unless there are clock screwups, when this function returns False it
        can be assumed the file has not changed. If it returns True it might or
        might not have been changed.
        """
        path = self.path / file_state.path

        exists_before = file_state.size is not None
        exists_now = path.exists()

        if not exists_before and not exists_now:
            # Nothing changed on the non-existance of this file in this
            # location.
            return False

        if exists_before != exists_now:
            # File either came into or vanished from existance, thats
            # definitely a change.
            return True

        assert exists_before and exists_now

        mtime = path.stat().st_mtime
        size = path.stat().st_size

        if file_state.mtime > mtime:
            logger.warn('Clock screwup: Memorized modification time of {} is more recent than actual.'.format(
                file_state.path
            ))
            # Default to treating the file as modified (always a safe choice in
            # terms of consistency, might just mean unnecessary scanning work).
            return True

        return mtime > file_state.mtime or size != file_state.size

    def generate_file_state(self, path):
        hasher = hashers.get_hasher('default')
        full_path = self.path / path
        exists = full_path.exists()

        if exists:
            mtime = full_path.stat().st_mtime
            size = full_path.stat().st_size
            with full_path.open('rb') as f:
                digest = hasher(f)

        else:
            mtime = size = digest = None

        r = FileState(
            path = self.normalize(path),
            mtime = mtime,
            size = size,
            digest = digest,
        )
        return r

