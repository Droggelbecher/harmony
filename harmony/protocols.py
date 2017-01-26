
import os.path
import shutil
import glob
from pathlib import Path

# TODO: Document, use metaclass or __init_subclass__ to automatically register protocols
# TODO: Implement first remote protocol
class Protocol:
    pass

# TODO: Document
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
        paths, cleanup = self.protocol.pull_working_files(self.location, paths, working_directory)
        self.cleanup_callbacks.append(cleanup)
        return paths

# TODO: Document
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
        location = str(location)
        if location.startswith('file://'):
            location = location[len('file://'):]
        location = os.path.abspath(location)
        return location

    def pull_harmony_files(self, location, paths):
        assert str(location) != '/'
        location = self.normalize_uri(location)
        r = {p: os.path.join(location, str(p)) for p in paths}, lambda: None
        return r

    def pull_working_files(self, location, paths, working_directory):
        working_directory = str(working_directory)
        for path in paths:
            path = str(path)
            shutil.copyfile(os.path.join(location, path), os.path.join(working_directory, path))
        return {p: os.path.join(working_directory, p) for p in paths}, lambda: None
        


_protocols = [FileProtocol()]

def get_protocols():
    return _protocols

def connect(location):
    assert isinstance(location, str) or isinstance(location, Path)
    location = str(location)
    for protocol in get_protocols():
        normalized = protocol.normalize_and_verify(location)
        if normalized is not None:
            return protocol.connect(normalized)
    return None

