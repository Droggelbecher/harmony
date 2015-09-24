
import os.path
import shutil
import glob

class Protocol:
    pass


class Connection:
    """
    Logical connection to a remote repository.
    Note that this usually shouldnt directly reflect a (network) connection
    (eg. in the TCP sense), as connections are often created solely for
    normalizing location specifications.
    """

    def __init__(self, protocol, location):
        self.protocol = protocol
        self.location = location

    def get_repository(self):
        return self.protocol.get_repository(self.location)

    def pull_state(self, commits_directory, remote_heads_directory):
        return self.protocol.pull_state(self.location, commits_directory,
                remote_heads_directory)

    def pull_file(self, path, working_directory):
        return self.protocol.pull_file(self.location, path, working_directory)

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

    def get_repository(self, location):
        from harmony import repository
        location = self.normalize_uri(location)
        repo = repository.Repository.find(location)
        assert repo is not None
        return repo

    def pull_state(self, location, commits_directory, heads_directory):
        location = self.normalize_uri(location)
        remote_repo = self.get_repository(location)

        for commit_fn in glob.glob(os.path.join(location, '.harmony/commits/*')):
            shutil.copyfile(commit_fn, os.path.join(commits_directory, os.path.basename(commit_fn)))

        shutil.copyfile(os.path.join(location, '.harmony/HEAD'), os.path.join(heads_directory, remote_repo.get_id()))
        return remote_repo

    def pull_file(self, location, path, working_directory):
        shutil.copyfile(os.path.join(location, path), os.path.join(working_directory, path))
        


_protocols = [FileProtocol()]

def get_protocols():
    return _protocols

def connect(location):
    for protocol in get_protocols():
        c = protocol.connect(location)
        if c is not None:
            return c
    return None

