
import os

from harmony.file_state import FileState
from harmony import hashers

class WorkingDirectory:

    # TODO: Test: any paths given out by this are already normalized correctly

    def __init__(self, path, ruleset):
        self.path = os.path.realpath(path)
        self.ruleset = ruleset

    def normalize(self, relpath):
        abspath = os.path.realpath(os.path.join(self.path, relpath))
        r = os.path.relpath(abspath, self.path)
        return r

    def get_filenames(self):
        r = set()
        for file_info in self.ruleset.iterate_committable_files(self.path):
            r.add(self.normalize(file_info.relative_filename))
        return r

    def __contains__(self, path):
        return os.path.exists(
            os.path.join(self.path, self.normalize(path))
        )

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
        path = os.path.join(self.path, file_state.path)

        exists_before = file_state.size is not None
        exists_now = os.path.exists(path)

        if not exists_before and not exists_now:
            # Nothing changed on the non-existance of this file in this
            # location.
            return False

        if exists_before != exists_now:
            # File either came into or vanished from existance, thats
            # definitely a change.
            return True

        assert exists_before and exists_now

        mtime = os.path.getmtime(path)
        size = os.path.getsize(path)

        # TODO: proper error handling (warn that there might be a clock
        # screwup)
        assert mtime >= file_state.mtime

        return mtime > file_state.mtime or size != file_state.size

    def generate_file_state(self, path):
        hasher = hashers.get_hasher('default')
        full_path = os.path.join(self.path, path)

        exists = os.path.exists(full_path)

        if exists:
            mtime = os.path.getmtime(full_path)
            size = os.path.getsize(full_path)
            with open(full_path, 'rb') as f:
                digest = hasher(f.read())

        else:
            mtime = size = digest = None

        r = FileState(
            path = self.normalize(path),
            mtime = mtime,
            size = size,
            digest = digest,
        )
        return r

