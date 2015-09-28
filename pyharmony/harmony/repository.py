
import os
import os.path
import socket
import logging
import uuid

from harmony import hashers
from harmony import protocols
from harmony import serialization
from harmony.history import History
from harmony.remotes import Remotes
from harmony.repository_state_exception import RepositoryStateException
from harmony.ruleset import Ruleset

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
        repo.history = History.init(repo.harmony_directory)
        repo.ruleset = Ruleset.init(repo.harmony_directory)
        repo.remotes = Remotes.init(repo.harmony_directory)

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
        repo.revision = repo_config['revision']

        repo.history = History.load(repo.harmony_directory)
        repo.ruleset = Ruleset.load(repo.harmony_directory)
        repo.remotes = Remotes.load(repo.harmony_directory)
        return repo

    @classmethod
    def clone(class_, working_directory, location, name = None):
        r = class_.init(working_directory, name)

        connection = protocols.connect(location)
        repo = connection.get_repository()
        r.remotes.add(location = connection.location, id_ = repo.get_id(), name = repo.get_name())

        r.pull_state(remote_specs = [location])
        r.write()
        return r
    


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

    def __init__(self,
            working_directory,
            harmony_directory = None
            ):
        self.working_directory = working_directory
        if harmony_directory is None:
            harmony_directory = Repository.find_harmony_directory(working_directory)
        self.harmony_directory = harmony_directory
        self.revision = 0
        
    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_url(self):
        return self.url

    def write(self):
        #self.history.write()
        self.remotes.write()
        self.ruleset.write()


        d = {
                'id': self.id,
                'name': self.name,
                'revision': self.revision,
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

    def commit(self, conflict_resolutions = None, dry_run = False):
        """
        DOCTODO
        """

        c = self.history.create_commit()
        parent = None

        # Copy repository info (remote file lists) from parent commits
        #

        if len(c.parents) == 1 or (len(c.parents) > 1 and conflict_resolutions is not None):
            # TODO: Think about how to actually deal with conflict solutions
            parent = self.history.get_commit(tuple(c.parents)[0])
            c.update_repositories(parent)
            c.inherit_files(parent)

        elif len(c.parents) > 1:
            # multiple parents?! We need to merge first!
            raise RepositoryStateException("The repository is in a multi-head state, merge first.")
        # Note: len(c.parents) == 0 can occur (first commit), and is fine.
        
        # Insert current repository state into commit
        #

        hashed_files = {}
        for file_info in self.ruleset.iterate_committable_files(self.working_directory):
            fn = file_info.relative_filename
            with open(file_info.absolute_filename, 'rb') as f:
                digest = hashers.get_hasher(file_info.rule['hasher'])(f.read())

            # If file changed since last commit, it is considered the newest
            # version of the file and committed.
            # (Independently of whether it matched the history version before)
            #
            # Otherwise, the history version is more recent, independently of
            # whether this file matches or matched the history version (might
            # have been outdated for several commits).

            if parent is None or parent.get_file(fn) != digest:
                c.update_file(fn, digest)
            hashed_files[fn] = digest

        c.update_repository(self, hashed_files)

        if (len(c.parents) == 1 and parent is not None and c.equal_state(parent)) \
                or (len(c.parents) == 0 and len(c.files) == 0):
            if not dry_run:
                logging.info('nothing changed.')

            return None

        else:
            if not dry_run:
                self.history.add_head(c)
                self.revision += 1
                self.write()

            return c


    def pull_state(self, remote_specs):
        """
        @param remote_specs list() or tuple() of remote specifications or a
        single remote specification (as string)
        """

        if isinstance(remote_specs, str):
            remote_specs = (remote_specs, )

        #
        # Preconditions
        #
        self.check_working_directory_clean()

        assert isinstance(remote_specs, list) \
                or isinstance(remote_specs, tuple)

        uris = self.history.find_remotes(remote_specs)
        connection = None
        for uri in uris:
            logging.info("pulling from {}...".format(uri))
            connection = protocols.connect(uri)

            if connection is not None:
                break

        assert connection is not None
        remote = connection.pull_state(self.history.commits_directory,
                self.history.remote_heads_directory)
        
        commit, conflicts = self.history.merge_remote(remote.get_id())

        if len(conflicts) == 0 and commit is not None:
            self.history.unset_merge_head_id()
            self.history.add_head(commit)
            
            #self.commit(conflict_resolutions = {})

        return conflicts



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
            #print(repository['id'], repository['name'])
            location = self.remotes.get_location(id_ = repository['id'], name
                    = repository['name'])
            assert location is not None
            connection = protocols.connect(location)
            assert connection is not None
            connection.pull_file(path, self.working_directory)


        




