
import os

from harmony.file_state import FileState
from harmony import hashers

class WorkingDirectory:

    def __init__(self, path, ruleset):
        self.path = os.path.abspath(path)
        self.ruleset = ruleset

    def get_filenames(self):
        r = set()
        for file_info in self.ruleset.iterate_committable_files(self.path):
            r.add(file_info.relative_filename)
        return r


    def file_maybe_modified(self, relative_ptah):
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
        mtime = os.path.getmtime(file_state.path)
        size = os.path.getsize(file_state.path)

        # TODO: proper error handling (warn that there might be a clock
        # screwup)
        assert mtime >= file_state.mtime

        return mtime > file_state.mtime or size != file_state.size

    def generate_file_state(self, path):
        hasher = hashers.get_hasher('default')
        full_path = os.path.join(self.path, path)

        mtime = os.path.getmtime(full_path)
        size = os.path.getsize(full_path)
        with open(full_path, 'rb') as f:
            digest = hasher(f.read())

        r = FileState()
        r.path = path
        r.mtime = mtime
        r.size = size
        r.digest = digest
        return r

