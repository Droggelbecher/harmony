
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

    def normalize_and_verify(self, location):
        return self.protocol.normalize_and_verify(location)

    # What we want to do:
    # - Get the remote repo metadata (id, name)
    # - Get the remotes location states
    # - Get content files
    #
    # What is the most useful interface common to all protocols for this?
    # a) One that can get us a number of files from remote?
    #    Protocol would do downloading/storing by itself and return just
    #    filenames, this would make it efficient to do local clones.
    #    Possibly distinguish between metadata and content files though.
    #
    #    (+) independent of serialization format, changes in internal directory
    #        structure etc...
    #    (-) dependent on local filesystem: ressources & permissions to write somewhere
    #    (-) dependent on remote filesystem layout & permissions
    #    (?) how to do cleanup of eg. tempfiles? how do we know its a temp?
    #        -> need more complicated return value
    #    (?) how to eg. get all location state files (whose names might not be
    #        known?)
    #        -> has to support recursive directory fetching as well
    #
    # b) Get stuff by-topic, ie. have a function for state, for 

    #def pull_states(self):
        #return self.protocol.pull_states(self.location)

    #def get_repository(self):
        #return self.protocol.get_repository(self.location)

    #def pull_state(self, commits_directory, remote_heads_directory):
        #return self.protocol.pull_state(self.location, commits_directory,
                #remote_heads_directory)

    def pull_harmony_files(self, paths):
        return self.protocol.pull_harmony_files(self.location, paths)

    def pull_working_files(self, paths, working_directory):
        return self.protocol.pull_file(self.location, paths, working_directory)

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

    #def get_repository(self, location):
        #from harmony import repository
        #location = self.normalize_uri(location)
        #repo = repository.Repository.find(location)
        #assert repo is not None
        #return repo

    def pull_harmony_files(self, location, paths):
        location = self.normalize_uri(location)

        return {
            p: {
                'local_path': os.path.join(location, p),
                'cleanup': lambda: None,
            } for p in paths
        }


        #pattern = os.path.join(
            #location,
            #Repository.HARMONY_SUBDIR,
            #LocationState.LocationState_SUBDIR,
            #'*'
        #)

        ## { location => { filename => { ... } } }
        #remote_location_states = {}

        #for filename in glob.glob(pattern):
            #state = LocationState.load(filename)
            #remote_location_states[state.location] = state

        #return remote_location_states


    #def pull_state(self, location, commits_directory, heads_directory):
        #location = self.normalize_uri(location)
        #remote_repo = self.get_repository(location)

        #for commit_fn in glob.glob(os.path.join(location, '.harmony/commits/*')):
            #shutil.copyfile(commit_fn, os.path.join(commits_directory, os.path.basename(commit_fn)))

        #sourcefile = os.path.join(location, '.harmony/HEAD')
        #if os.path.exists(sourcefile):
            #shutil.copyfile(sourcefile, os.path.join(heads_directory, remote_repo.get_id()))
        #return remote_repo

    def pull_working_files(self, location, paths, working_directory):
        for path in paths:
            shutil.copyfile(os.path.join(location, path), os.path.join(working_directory, path))
        


_protocols = [FileProtocol()]

def get_protocols():
    return _protocols

def connect(location):
    for protocol in get_protocols():
        normalized = protocol.normalize_and_verify(location)
        if normalized is not None:
            return protocol.connect(normalized)
    return None

