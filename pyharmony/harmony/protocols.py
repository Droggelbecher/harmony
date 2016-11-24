
import os.path
import shutil
import glob

class Protocol:
    pass


class Connection:

    def __init__(self, protocol, location):
        self.protocol = protocol
        self.location = location

    def __enter__(self):
        self.cleanup_callbacks = []
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def cleanup(self):
        for c in self.cleanup_callbacks:
            c()
        self.cleanup_callbacks = []

    def normalize_and_verify(self, location):
        return self.protocol.normalize_and_verify(location)

    def pull_harmony_files(self, paths):
        paths, cleanup = self.protocol.pull_harmony_files(self.location, paths)
        self.cleanup_callbacks.append(cleanup)
        return paths

    def pull_working_files(self, paths, working_directory):
        paths, cleanup = self.protocol.pull_file(self.location, paths, working_directory)
        self.cleanup_callbacks.append(cleanup)
        return paths

class FileProtocol(Protocol):

    def connect(self, location):
        location = self.normalize_and_verify(location)
        if location is None:
            return None

        return Connection(
                protocol = self,
                location = location
                )

    def normalize_and_verify(self, location):
        location = self.normalize_uri(location)
        if os.path.isdir(location):
            return location
        return None

    def normalize_uri(self, location):
        if location.startswith('file://'):
            location = location[len('file://'):]
        location = os.path.abspath(location)
        return location

    def pull_harmony_files(self, location, paths):
        assert location != '/'
        location = self.normalize_uri(location)
        return {p: os.path.join(location, p) for p in paths}, lambda: None

    def pull_working_files(self, location, paths, working_directory):
        for path in paths:
            shutil.copyfile(os.path.join(location, path), os.path.join(working_directory, path))
        


_protocols = [FileProtocol()]

def get_protocols():
    return _protocols

def connect(location):
    assert isinstance(location, str)
    for protocol in get_protocols():
        normalized = protocol.normalize_and_verify(location)
        if normalized is not None:
            return protocol.connect(normalized)
    return None

