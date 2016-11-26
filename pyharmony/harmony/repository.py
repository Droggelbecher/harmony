
import os
import os.path
import socket
import logging
import uuid
from collections import defaultdict

from harmony import hashers
from harmony import protocols
from harmony import serialization
from harmony.location_state import LocationState
from harmony.remotes import Remotes
from harmony.repository_state_exception import RepositoryStateException
from harmony.ruleset import Ruleset
from harmony.working_directory import WorkingDirectory
from harmony.file_state import FileState

class Repository:

    HARMONY_SUBDIR = '.harmony'
    REPOSITORY_FILE = 'config'

    #
    # Factory classmethods (returning Repository instances)
    #

    @classmethod
    def init(class_, working_directory, name = None):
        """
        Create fresh repository in given working dir.

        @return Repository instance for created repo.
        """

        harmony_directory = class_.find_harmony_directory_here(working_directory)
        working_directory = class_.find_working_directory_here(working_directory)

        if name is None:
            name = class_.generate_name(working_directory)

        os.mkdir(harmony_directory)


        repo = Repository(working_directory, harmony_directory)

        def make_component(class_):
            return class_.init(
                class_.get_path(repo.harmony_directory)
            )

        repo.location_state = make_component(LocationState)
        repo.ruleset = make_component(Ruleset)
        repo.remotes = make_component(Remotes)
        repo.working_directory = WorkingDirectory(working_directory, repo.ruleset)

        repo.id = uuid.uuid1().hex
        repo.name = name

        repo.write()

        return repo

    @classmethod
    def find(class_, working_directory):
        """
        Find repository configuration data in a parent dir of given working
        dir and create repository instance for it.

        @return Repository instance for repo around working_directory.
        """

        harmony_directory = class_.find_harmony_directory(working_directory)
        return class_.load(harmony_directory)

    @classmethod
    def load(class_, harmony_directory):
        """
        @return Repository instance for repo in working_directory.
        """
        working_directory = class_.find_working_directory_here(harmony_directory)
        repo = class_(working_directory, harmony_directory)

        repo_config = serialization.read(os.path.join(harmony_directory, Repository.REPOSITORY_FILE))

        repo.id = repo_config['id']
        repo.name = repo_config['name']

        def load_component(class_):
            return class_.load(
                class_.get_path(repo.harmony_directory)
            )

        repo.location_state = load_component(LocationState)
        repo.ruleset = load_component(Ruleset)
        repo.remotes = load_component(Remotes)
        repo.working_directory = WorkingDirectory(working_directory, repo.ruleset)

        return repo

    @classmethod
    def clone(class_, working_directory, location, name = None):
        # Create empty repo $r in target location
        target_repo = class_.init(working_directory, name)
        config_path = os.path.join(class_.HARMONY_SUBDIR, class_.REPOSITORY_FILE)

        with protocols.connect(location) as connection:
            files = connection.pull_harmony_files([config_path])
            # Read remote repository configuration from downloaded file
            source_config = serialization.read(files[config_path])

        # Add source repo as remote
        target_repo.remotes.add(
            location = location,
            id_ = source_config['id'],
            name = source_config['name']
        )

        # Pull
        target_repo.pull_state(location)
        target_repo.write()

        return target_repo

    #
    # General-purpose classmethods
    #

    @classmethod
    def generate_name(class_, working_directory):
        return '{}-{}'.format(socket.gethostname(), os.path.basename(working_directory))

    @classmethod
    def find_harmony_directory_here(class_, working_directory):
        if os.path.basename(working_directory) == class_.HARMONY_SUBDIR:
            return working_directory
        return os.path.join(working_directory, class_.HARMONY_SUBDIR)

    @classmethod
    def find_harmony_directory(class_, working_directory):
        search_start = working_directory

        # Traverse directories upwards until a '.harmony' subdir is
        # encountered.
        # Stop as mountpoints or when the current directory is not an existing
        # directory anymore (shouldnt happen in a sane filesystem)

        harmony_dir = None
        working_directory = os.path.abspath(working_directory)
        while os.path.isdir(working_directory) and not os.path.ismount(working_directory):
            d = os.path.join(working_directory, class_.HARMONY_SUBDIR)
            if os.path.isdir(d):
                harmony_dir = d
                break
            working_directory = os.path.join(working_directory, os.path.pardir)
            working_directory = os.path.abspath(working_directory)

        if harmony_dir is None:
            raise FileNotFoundError('No harmony repository found in "{}".  Search stopped in "{}"'.format(
                search_start, working_directory))
        return harmony_dir

    @classmethod
    def find_working_directory_here(class_, working_directory):
        if os.path.basename(working_directory) == class_.HARMONY_SUBDIR:
            return os.path.join(working_directory, '..')
        return working_directory


    # =======================================================
    #
    # Methods
    #
    # =======================================================

    def __init__(self, working_directory, harmony_directory = None):
        """
        This constructor alone is not sufficient to create a usable Repository
        instance, use Repository.init or Repository.load.
        """
        if harmony_directory is None:
            harmony_directory = Repository.find_harmony_directory(working_directory)
        self.harmony_directory = harmony_directory


    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_url(self):
        return self.url

    def write(self):
        self.location_state.write()
        self.remotes.write()
        self.ruleset.write()

        d = {
                'id': self.id,
                'name': self.name,
                }
        serialization.write(d, os.path.join(self.harmony_directory, Repository.REPOSITORY_FILE))

    #
    # Actual repository operations
    #

    def check_working_directory_clean(self):
        """
        Raise a RepositoryStateException if any of the following are NOT met:
        - There is no MERGE_HEAD
        - There are no uncommitted changes in the working directory

        """
        c = self.commit(dry_run = True)
        if c is not None:
            raise RepositoryStateException("Working directory not clean, commit first.")

    def commit(self, dry_run = False):
        """
        DOCTODO
        """

        # TODO: Detect renames and generate WIPE entries accordingly (see
        # design/design_questions.txt)

        working_directory = self.working_directory

        paths = working_directory.get_filenames()

        # Create a commit based on the last known state
        self.location_state.create_state(self.id)

        # Now go consider all the files that are in our record (and might or
        # might not still be there) plus all the files that are in the working
        # directory (and might or might not have an earlier state committed)

        paths = set(self.location_state.get_all_paths(id_ = self.id)).union(
            working_directory.get_filenames()
        )

        for path in paths:
            file_state = self.location_state.get_latest_file_state(path)
            if working_directory.file_maybe_modified(file_state):
                new_file_state = working_directory.generate_file_state(file_state.path)
                self.location_state.update_file_state(self.id, new_file_state)

        if not self.location_state.was_modified(self.id):
            return False

        if not dry_run:
            self.location_state.write()

        return True


    def pull_state(self, remote_spec):
        """
        @param remote_specs list() or tuple() of remote specifications or a
        single remote specification (as string)
        """
        config_path = os.path.join(self.HARMONY_SUBDIR, self.REPOSITORY_FILE)
        states_path = LocationState.get_path(self.HARMONY_SUBDIR)

        # TODO: How to even pull from many locations?
        #
        location = self.remotes.get_location_any(remote_spec)

        with protocols.connect(location) as connection:
            files = connection.pull_harmony_files([config_path, states_path])
            remote_id = serialization.read(files[config_path])['id']
            remote_history = LocationState.load(files[states_path])

        conflicts = self.merge(remote_id, remote_history)

        # TODO: make these nicer (without outside access to $state)
        #self.location_state.state.update(new_state)

        self.location_state.write()

        print('conflicts={}'.format(conflicts))
        return conflicts


    def fetch(self, remote_state):
        # TODO: Just copy over all newer remote states,
        # state about local repo should never be overwritten by this operation.


    def find_conflicts(self):
        # TODO: Find all conflicts (situations where there is more than one
        # head for a file)
        # Note: resolving conflicts is than done by a commit()


    def merge(self, remote_id, remote_location_state):
        # TODO: refactor this into fetch() and find_conflicts()
        # to reduce my own confusion about what this is supposed to do

        remote_locations = remote_location_state.get_locations()
        local_locations = self.location_state.get_locations()

        paths = set(self.location_state.get_all_paths()).union(
            remote_location_state.get_all_paths()
        )

        locations = set(self.location_state.get_locations()).union(
            remote_location_state.get_locations()
        )

        conflicts = {}

        #rec_dd = lambda: defaultdict(rec_dd)
        #new_state = rec_dd()

        # TODO: handle WIPE entries

        for path in paths:
            entries = set()

            for location in locations:
                # "entry" here means FileState
                # For each path/location combo, we have a local "idea" of what
                # the state of that file at that location is and one remote.
                # This is to figure out which entry to use in which case.

                local_entry = self.location_state.get_file_state(self.id, path)
                remote_entry = remote_location_state.get_file_state(remote_id, path)

                assert not (local_entry is None and remote_entry is None)

                new_entry = None
                if local_entry is None:
                    new_entry = remote_entry

                elif remote_entry is None:
                    new_entry = local_entry

                # Yes it should have, if we assume that is correct, it should
                # also work with just the else branch though.
                # If we want a thorough plausibility check that should probably
                # be a seperate function anyway.
                elif location == self.id:
                    # Local location hast most up to date info on itself
                    # TODO: assert clock says the same thing
                    new_entry = local_entry

                # Remote doesnt always have an id.
                # We dont always have a remote id.
                # We could get it by pulling the remotes config, however this
                # branch should anyways be covered by the one below.
                elif location == remote_id:
                    new_entry = remote_entry

                else:
                    comparison = local_entry.compare_clock(remote_entry)

                    if comparison == 0:
                        # if clocks are equal, than digest, size and mtime should
                        # be, too.
                        assert local_entry.digest == remote_entry.digest
                        assert local_entry.size == remote_entry.size
                        assert local_entry.mtime == remote_entry.mtime
                        # Any will do
                        new_entry = local_entry

                    elif comparison < 0:
                        new_entry = remote_entry

                    elif comparison > 0:
                        new_entry = local_entry

                    else: # uncomparable / None
                        # This means that not only are there two different
                        # views on what the state of $path in $location is,
                        # This should not be possible if the clock values were
                        # only manipulated by $location. See
                        # design/design_questions.txt ("How did this merge work?")
                        assert False

                self.location_state.update_file_state(self.id, new_entry)
                #new_state[location]['files'][path] = new_entry
                entries.add(new_entry)

            heads = FileState.get_heads(entries)
            assert len(heads) >= 1
            if len(heads) > 1:
                conflicts[path] = heads

        #for location_id, d in new_state.items():
            #d['location'] = location_id
            #d['modified'] = True

        return conflicts #, new_state

        #if isinstance(remote_specs, str):
            #remote_specs = (remote_specs, )

        ##
        ## Preconditions
        ##
        #self.check_working_directory_clean()

        #assert isinstance(remote_specs, list) \
                #or isinstance(remote_specs, tuple)

        #uris = [self.remotes.get_location_any(r) for r in remote_specs]

        #connection = None
        #for uri in uris:
            #logging.info("pulling from {}...".format(uri))
            #connection = protocols.connect(uri)

            #if connection is not None:
                #break

        #assert connection is not None
        #remote = connection.pull_state(self.history.commits_directory,
                #self.history.remote_heads_directory)
        
        #commit, conflicts = self.history.merge_remote(remote.get_id())

        #if len(conflicts) == 0 and commit is not None:
            #self.history.unset_merge_head_id()
            #self.history.add_head(commit)
            
            ##self.commit(conflict_resolutions = {})

        #return conflicts



    def pull_file(self, path):
        head = self.history.get_local_head()
        assert head is not None

        # TODO: transform path to be sure its relative to working directory

        digest = head.get_file(path)
        assert digest is not None

        candidate_repositories = (
                r for r in head.repositories.values()
                if r['files'].get(path, None) == digest
        )

        for repository in candidate_repositories:
            location = self.remotes.get_location(id_ = repository['id'], name
                    = repository['name'])
            assert location is not None
            connection = protocols.connect(location)
            assert connection is not None
            connection.pull_working_file((path,), self.working_directory.path)


        




