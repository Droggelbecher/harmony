
import os
import os.path
import socket
import logging
import uuid
from collections import defaultdict

from harmony import hashers
from harmony import protocols
from harmony import serialization
from harmony.location_states import LocationStates
from harmony.repository_state import RepositoryState
from harmony.remotes import Remotes
from harmony.repository_state_exception import RepositoryStateException
from harmony.ruleset import Ruleset
from harmony.working_directory import WorkingDirectory

logger = logging.getLogger(__name__)

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
            logging.debug('make_companent {}'.format(class_.get_path(repo.harmony_directory)))
            return class_.init(
                class_.get_path(repo.harmony_directory)
            )

        repo.location_states = make_component(LocationStates)
        repo.repository_state = make_component(RepositoryState)
        repo.ruleset = make_component(Ruleset)
        repo.remotes = make_component(Remotes)
        repo.working_directory = WorkingDirectory(working_directory, repo.ruleset)

        repo.id = uuid.uuid1().hex
        repo.name = name

        repo.save()

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

        # TODO: implement a Configuration class so we can use
        # Configuration.load(...) here
        repo_config = serialization.read(os.path.join(harmony_directory, Repository.REPOSITORY_FILE))

        repo.id = repo_config['id']
        repo.name = repo_config['name']

        def load_component(class_):
            logging.debug('load_component {}'.format(class_.get_path(repo.harmony_directory)))
            return class_.load(
                class_.get_path(repo.harmony_directory)
            )

        repo.location_states = load_component(LocationStates)
        repo.repository_state = load_component(RepositoryState)
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
        target_repo.save()

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

    def save(self):
        self.location_states.save()
        self.repository_state.save()
        self.remotes.save()
        self.ruleset.save()

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
        logger.debug('COMMIT {}'.format(self.id))
        logger.debug('working dir {}'.format(self.working_directory.path))

        # TODO: Detect renames and generate WIPE entries accordingly (see
        # design/design_questions.txt)

        # TODO: When adding a new file that is also present in the repository
        # in a different location with a different hash, optionally warn/ask,
        # as the user might not have checked whether this filename is in the
        # repo before adding.
        # Give options to
        # - download the most up-to-date version from the repo for comparison
        # - rename file before committing
        # - just accept the added version as most up-to-date
        # - don't include the added file in the commit
        # - remove the to-be-added file (physically), as user now understands
        #   he/she doesn't need that version anymore
        #
        # Note: While this is technically similar to merging, it is a slightly
        # different thing as it doesnt compare two committed states but one
        # committed and a to-be-committed.

        working_directory = self.working_directory
        paths = working_directory.get_filenames()


        # 1. update location state
        #    - TODO detect renames (add WIPE entries later for those)
        #    - TODO when a file is *added* that is known to other locations w/
        #      different digest, let user confirm what he wants to do (see
        #      above)
        #    - increase local clock
        #
        # 2. update repository state
        #    - if file changed in step 1:
        #      clock = current clock for local + max for each other location
        #      hash = current local hash
        #      (deviate from this if user selected to do something else)
        #    - if file did not change:
        #      no change in hash or clock

        any_change = False
        for path in paths:
            file_state = self.location_states.get_file_state(self.id, path)
            if working_directory.file_maybe_modified(file_state):
                new_file_state = working_directory.generate_file_state(file_state.path)
                changed = self.location_states.update_file_state(self.id, new_file_state)
                if changed:
                    any_change = True
                    self.repository_state.update_file_state(
                        new_file_state,
                        self.id,
                        self.location_states.get_clock(self.id) + 1,
                    )
                    logger.debug('{} committed: {} clk={}'.format(self.id, new_file_state.path, self.location_states.get_clock(self.id) + 1))
                else:
                    logger.debug('{} not actually changed: {}'.format(self.id, path))
            else:
                logger.debug('{} not changed: {}'.format(self.id, path))

        self.location_states.save()
        self.repository_state.save()

        logger.debug('/COMMIT {} any_change={}'.format(self.id, any_change))

        return any_change

    def pull_state(self, remote_spec):
        """
        @param remote_specs list() or tuple() of remote specifications or a
        single remote specification (as string)
        """
        remote_repository_state = self.fetch(remote_spec)
        conflicts, new_repository_state = self.merge(remote_repository_state)

        logger.debug('conflicts={}'.format(conflicts))
        if not len(conflicts):
            logger.debug('auto-merging')
            self.repository_state.overwrite(new_repository_state)
            self.repository_state.save()

        return conflicts


    def fetch(self, remote_spec):
        location = self.remotes.get_location_any(remote_spec)

        logger.debug('{} fetching from {} which is at {}'.format(
            self.id, remote_spec, location
        ))

        #config_path = os.path.join(self.HARMONY_SUBDIR, self.REPOSITORY_FILE)
        location_states_path = LocationStates.get_path(self.HARMONY_SUBDIR)
        repository_state_path = RepositoryState.get_path(self.HARMONY_SUBDIR)


        with protocols.connect(location) as connection:
            files = connection.pull_harmony_files([
                location_states_path,
                repository_state_path
            ])
            remote_location_states = LocationStates.load(files[location_states_path])
            repository_state = RepositoryState.load(files[repository_state_path])

        logger.debug('{} fetched remote state:'.format(self.id))
        for lid, location in remote_location_states.items.items():
            logger.debug('  {}:'.format(lid))
            for f in location.files.values():
                logger.debug('    {}'.format(f))

        self.location_states.update(remote_location_states)
        self.location_states.save()

        return repository_state


    def merge(self, remote_repository_state):
        local_paths = set(self.repository_state.get_paths())
        remote_paths = set(remote_repository_state.get_paths())
        local_state = self.repository_state
        remote_state = remote_repository_state

        merged = RepositoryState(None)
        conflicts = {}

        # TODO: clean up all logger messages (also in other modules)

        logger.debug('ID {}'.format(self.id))
        logger.debug('paths local={}'.format(self.repository_state.get_paths()))
        logger.debug('paths remote={}'.format(remote_repository_state.get_paths()))

        for p in local_paths - remote_paths:
            merged.set_entry( p, local_state.get_entry(p) )

        for p in remote_paths - local_paths:
            merged.set_entry( p, remote_state.get_entry(p) )


        # conflicts can only arise in paths that are specified in both state
        # files
        paths = set(self.repository_state.get_paths()) \
                & set(remote_repository_state.get_paths())


        for path in paths:
            local = self.repository_state.get_entry(path)
            remote = remote_repository_state.get_entry(path)

            c = local.clock.compare(remote.clock)
            logger.debug('  path={} l.c={} r.c={} cmp={}'.format(
                path, local.clock, remote.clock, c
            ))

            if c is None:
                if local.contents_different(remote):
                    conflicts[path] = (local, remote)
                else:
                    # TODO: Create a new, merged clock value!
                    merged.set_entry(path, local)

            elif c < 0:
                merged.set_entry(path, remote)

            else: # c >= 0:
                merged.set_entry(path, local)

        return conflicts, merged


    def pull_file(self, path, remote_spec):

        location = self.remotes.get_location_any(remote_spec)
        with protocols.connect(location) as connection:
            connection.pull_working_files([path], self.working_directory.path)

        self.commit()

