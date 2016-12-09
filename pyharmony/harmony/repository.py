
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
from harmony.util import short_id

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

    @property
    def short_id(self):
        """
        Provide a shortened version of the ID for easier reconizability
        in log messages.
        Much more likely to collide for many repos, but incredibly useful for
        quickly understanding logs of unittests.
        """
        return short_id(self.id)

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
        logger.debug('<commit> ID={} WD={}'.format(self.short_id, self.working_directory.path))

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
        paths = set(working_directory.get_filenames()) \
                | set(self.location_states.get_all_paths(self.id))


        # 1. update location state
        #    - detect renames (add WIPE entries later for those)
        #    - when a file is *added* that is known to other locations w/
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


        # Do all the file scanning before so we can be sure to do it at most
        # once per file in the WD
        wd_states = {
            path: working_directory.generate_file_state(path)
            for path in paths
            if working_directory.file_maybe_modified(
                self.location_states.get_file_state(self.id, path)
            )
        }

        location_states = {
            path: self.location_states.get_file_state(self.id, path)
            for path in paths
        }


        any_change = False
        for path in paths:

            if path in wd_states:
                file_state = location_states[path]
                new_file_state = wd_states[path]
                changed = self.location_states.update_file_state(self.id, new_file_state)
                if changed:
                    any_change = True

                    # If the file vanished but a new one with the same digest
                    # popped up, consider that a rename.
                    # Rename means, the new file is WIPEd (instead of just
                    # locally removed) and the new file is added as usual
                    if not new_file_state.exists():
                        logger.debug('{} vanished'.format(new_file_state.path))
                        for path2 in paths:
                            if path2 == path: continue
                            path2_state = location_states[path2]
                            new_path2_state = wd_states[path2]
                            logger.debug('{} rename candidate {} ex before={} ex now={} self.digest={} candidate.digest={}'.format(
                                path, path2, path2_state.exists(),
                                new_path2_state.exists(),
                                file_state.digest, new_path2_state.digest
                            ))

                            if not path2_state.exists() \
                               and new_path2_state.exists() \
                               and new_path2_state.digest == file_state.digest:
                                logger.info('Detected rename: {} -> {}'.format(path, path2))
                                new_file_state.wipe = True
                                new_file_state.digest = file_state.digest
                                break

                    self.repository_state.update_file_state(
                        new_file_state,
                        self.id,
                        self.location_states.get_clock(self.id) + 1,
                    )
                    logger.debug('{} committed: {} clk={}'.format(self.short_id, new_file_state.path, self.location_states.get_clock(self.id) + 1))
                else:
                    logger.debug('{} not actually changed: {}'.format(self.short_id, path))
            else:
                logger.debug('{} not changed: {}'.format(self.short_id, path))

        self.location_states.save()
        self.repository_state.save()

        logger.debug('</commit> ID={} any_change={}'.format(self.short_id, any_change))
        return any_change

    def pull_state(self, remote_spec):
        logger.debug('{} pull from {}'.format(self.short_id, remote_spec))
        remote_repository_state = self.fetch(remote_spec)
        conflicts, new_repository_state = self.merge(remote_repository_state)

        logger.debug('conflicts={}'.format(list(conflicts.keys())))
        if not len(conflicts):
            logger.debug('auto-merging')
            self.repository_state.overwrite(new_repository_state)
            self.repository_state.save()
            self.auto_rename()

        return conflicts

    def auto_rename(self):
        # precondition: WD clean

        # Automatically apply auto-renaming
        # Auto-renaming
        # -------------
        # 1. Find any files $A with a WIPE entry.
        # 2. Compute/get their digest (from location state)
        # 3. Find a non-wiped file $B in repo that does not exist in the WD
        # 4. Rename $A to $B

        for path, entry in self.repository_state.files.items():
            if entry.wipe and (entry.path in self.working_directory):
                possible_targets = {
                    e.path for e in self.repository_state.files.values()
                    if e.path != path and e.digest == entry.digest and not e.wipe
                }
                logger.info(
                    '{} could be auto-renamed to any of {}'.format(
                        path, possible_targets
                    )
                )
                if possible_targets:
                    os.rename(
                        os.path.join(self.working_directory.path, path),
                        os.path.join(self.working_directory.path, possible_targets.pop())
                    )

        # TODO: Update location state to reflect whats happened here and test
        # that



    def fetch(self, remote_spec):
        location = self.remotes.get_location_any(remote_spec)

        logger.debug('{} fetching from {} which is at {}'.format(
            self.short_id, remote_spec, location
        ))

        location_states_path = LocationStates.get_path(self.HARMONY_SUBDIR)
        repository_state_path = RepositoryState.get_path(self.HARMONY_SUBDIR)

        with protocols.connect(location) as connection:
            files = connection.pull_harmony_files([
                location_states_path,
                repository_state_path
            ])
            remote_location_states = LocationStates.load(files[location_states_path])
            repository_state = RepositoryState.load(files[repository_state_path])

        logger.debug('{} fetched remote state:'.format(self.short_id))
        for lid, location in remote_location_states.items.items():
            logger.debug('  {}:'.format(short_id(lid)))
            for f in location.files.values():
                logger.debug('    {}'.format(f.__dict__))

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
            if c is None:
                if local.contents_different(remote):
                    logger.debug('merge: {} in conflict: {} <-> {}'.format(
                        path, local.clock, remote.clock
                    ))
                    conflicts[path] = (local, remote)
                else:
                    logger.debug('merge: {} automerged (same content)'.format(path))
                    # TODO: Create a new, merged clock value!
                    merged.set_entry(path, local)

            elif c < 0:
                logger.debug('merge: {} newer on remote'.format(path))
                merged.set_entry(path, remote)

            else: # c >= 0:
                logger.debug('merge: {} same version or newer on local'.format(path))
                merged.set_entry(path, local)

        return conflicts, merged


    def pull_file(self, path, remote_spec):

        location = self.remotes.get_location_any(remote_spec)
        with protocols.connect(location) as connection:
            connection.pull_working_files([path], self.working_directory.path)

        self.commit()

