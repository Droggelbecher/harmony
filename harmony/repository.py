
"""
API entry points for Harmony.
Use these to work with Harmony programmatically.
"""

import os
from pathlib import Path
import socket
import logging
import uuid
from typing import Optional, Dict, Tuple, Union

from harmony import protocols
from harmony import serialization
from harmony import file_state_logic
from harmony.location_states import LocationStates
from harmony.repository_state import RepositoryState, RepositoryFileState
from harmony.remotes import Remotes
from harmony.ruleset import Ruleset
from harmony.working_directory import WorkingDirectory
from harmony.util import shortened_id, has_suffix

logger = logging.getLogger(__name__)

class Repository:
    """
    Main Harmony API entry point.
    Represents all the functionality and data available from a local Location.
    That is:
    - Management of (locally known) remotes
    - Initializing & Cloning locations (including repo state, etc..)
    - Pulling files & states from remote locations
    """

    HARMONY_SUBDIR = Path('.harmony')
    REPOSITORY_FILE = Path('config')

    location_states: LocationStates
    repository_state: RepositoryState
    ruleset: Ruleset
    remotes: Remotes
    working_directory: WorkingDirectory
    id: str
    name: Optional[str]

    #
    # Factory classmethods (returning Repository instances)
    #

    @classmethod
    def init(class_, working_directory: Path, name: Optional[str] = None) -> 'Repository':
        """
        Create fresh repository in given working dir.

        @return Repository instance for created repo.
        """

        harmony_directory = class_.find_harmony_directory_here(working_directory)
        working_directory = class_.find_working_directory_here(working_directory)

        if name is None:
            name = class_.generate_name(working_directory)

        harmony_directory.mkdir()

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

        logging.info('Initialized repository')
        logging.info(f'  ID  : {repo.short_id} ({repo.id})')
        logging.info(f'  Name: {repo.name}')
        logging.info(f'  WD  : {repo.working_directory.path}')

        repo.save()

        return repo

    @classmethod
    def find(class_, working_directory: Path) -> 'Repository':
        """
        Find repository configuration data in a parent dir of given working
        dir and create repository instance for it.

        @return Repository instance for repo around working_directory.
        """

        harmony_directory = class_.find_harmony_directory(working_directory)
        return class_.load(harmony_directory)

    @classmethod
    def load(class_, harmony_directory: Path) -> 'Repository':
        """
        @return Repository instance for repo in working_directory.
        """
        harmony_directory = Path(harmony_directory)

        working_directory = class_.find_working_directory_here(harmony_directory)
        repo = class_(working_directory, harmony_directory) # type: ignore

        # TODO: implement a Configuration class so we can use
        # Configuration.load(...) here
        repo_config = serialization.read(harmony_directory / Repository.REPOSITORY_FILE)

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

        logging.info('Loaded repository')
        logging.info(f'  ID  : {repo.short_id} ({repo.id})')
        logging.info(f'  Name: {repo.name}')
        logging.info(f'  WD  : {repo.working_directory.path}')

        return repo

    @classmethod
    def clone(class_, target_directory: Path, source_directory: Path, name: Optional[str] = None) \
                -> 'Repository':
        """
        Clone a repository from $location into $working_directory.
        """

        # Create empty repo $r in target location
        target_repo = class_.init(target_directory, name)
        config_path = class_.HARMONY_SUBDIR / class_.REPOSITORY_FILE
        source_directory = source_directory.resolve()

        with protocols.connect(source_directory) as connection:
            files = connection.pull_harmony_files([config_path])
            # Read remote repository configuration from downloaded file
            source_config = serialization.read(files[config_path])

        # Add source repo as remote
        target_repo.remotes.add(
            location=source_directory,
            id=source_config['id'],
            name=source_config['name']
        )

        # Pull
        target_repo.pull_state(source_directory)
        target_repo.save()

        return target_repo

    #
    # General-purpose classmethods
    #

    @classmethod
    def generate_name(class_, working_directory: Path) -> str:
        """
        Generate a suitable name for a new repository in the given $working_directory
        """
        return '{}-{}'.format(socket.gethostname(), working_directory.name.replace(' ', '-'))

    @classmethod
    def find_harmony_directory_here(class_, directory: Path) -> Path:
        """
        Given a working directory path or harmony directory path,
        return the harmony directory path of the according location.
        (I.e. $directory or $directory / .harmony)
        """
        if has_suffix(directory, class_.HARMONY_SUBDIR):
            return directory
        return directory / class_.HARMONY_SUBDIR

    @classmethod
    def find_harmony_directory(class_, directory: Path) -> Path:
        """
        Given a path to a directory that is a subpath of a locations working directory,
        find the harmony directory of the according location.
        """

        search_start = directory

        # Traverse directories upwards until a '.harmony' subdir is
        # encountered.
        # Stop as mountpoints or when the current directory is not an existing
        # directory anymore (shouldnt happen in a sane filesystem)

        harmony_dir = None
        directory = directory.resolve()
        while directory.is_dir() and not os.path.ismount(str(directory)):
            d = directory / class_.HARMONY_SUBDIR
            if d.is_dir():
                harmony_dir = d
                break
            directory = directory.parent.resolve()

        if harmony_dir is None:
            raise FileNotFoundError(
                f'No harmony repository found in "{search_start}". Search stopped in "{directory}"'
            )
        return harmony_dir

    @classmethod
    def find_working_directory_here(class_, directory: Path) -> Path:
        """
        Given a working directory path or harmony directory path,
        return the working directory path of the according location
        (i.e. $directory or $directory/..)
        """
        if has_suffix(directory, class_.HARMONY_SUBDIR):
            return directory.parent.resolve()
        return directory


    # =======================================================
    #
    # Methods
    #
    # =======================================================

    def __init__(self, working_directory: Path, harmony_directory: Optional[Path] = None) -> None:
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
        return shortened_id(self.id)

    def save(self):
        """
        Save all (location, repository, remotes, ruleset) state to disk.
        """
        self.location_states.save()
        self.repository_state.save()
        self.remotes.save()
        self.ruleset.save()

        d = {
            'id': self.id,
            'name': self.name,
        }
        serialization.write(d, self.harmony_directory / Repository.REPOSITORY_FILE)

    #
    # Actual repository operations
    #

    def commit(self, Stats=None) -> bool:
        """
        Scan file states and commit to location state and repository state.
        Return True iff the commit denotes an actual change.

        Stats: Optional class with constructor(total_bytes) and .update(bytes_scanned) method
            for progress feedback.
        """
        logger.debug(f'{self.short_id} committing...')
        any_change = file_state_logic.commit(
            self.id,
            self.working_directory,
            self.location_states,
            self.repository_state,
            Stats,
        )

        self.location_states.save()
        self.repository_state.save()
        logger.debug(f'{self.short_id} committed. Changes seen: {any_change}')
        return any_change

    def pull_state(self, remote_spec: Union[str, Path]) \
        -> Dict[
                Path,
                Tuple[RepositoryFileState, RepositoryFileState]
        ]:
        """
        Pull state from remote location $remote_spec.
        Return a dictionary about all encountered conflicts of form
        {path: (local file state, remote file state), ...}
        """
        logger.debug('{self.short_id} pull from {remote_spec}')
        remote_repository_state = self.fetch(remote_spec)
        conflicts, new_repository_state = file_state_logic.merge(
            local_state=self.repository_state,
            remote_state=remote_repository_state,
            merger_id=self.id
        )

        logger.debug(f'conflicts={list(conflicts.keys())}')
        if not conflicts:
            logger.debug('auto-merging')
            self.repository_state.overwrite(new_repository_state)
            self.repository_state.save()
            file_state_logic.auto_rename(self.working_directory,
                                         self.repository_state)
            # Commit changes done by auto_rename
            self.commit()

        return conflicts

    def fetch(self, remote_spec):
        location = self.remotes.get_location_any(remote_spec)

        logger.debug('{} fetching from {} which is at {} to {}'.format(
            self.short_id, remote_spec, location,
            self.harmony_directory
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
            logger.debug('  {}:'.format(shortened_id(lid)))
            for f in location.files.values():
                logger.debug('    {}'.format(f.__dict__))

        self.location_states.update(remote_location_states)
        self.location_states.save()

        return repository_state

    def pull_file(self, path, remote_spec):
        location = self.remotes.get_location_any(remote_spec)
        with protocols.connect(location) as connection:
            connection.pull_working_files([path], self.working_directory.path)

        self.commit()

    def add_remote(self, name, location, id=None):
        self.remotes.add(
            location=location,
            name=name,
            id=id
        )
        self.remotes.save()

    def remove_remote(self, name):
        # TODO: Linter is right, this does not exist,
        # write a test for it & implement!
        self.remotes.remove(
            name=name
        )
        self.remotes.save()

    def get_remotes(self):
        return self.remotes.get_remotes()


    class FileStatus:
        """
        Status of a file that is in the local working directory or the abstract
        repository (or both)
        """
        path: Path
        exists_in_repository: bool
        maybe_modified: bool
        exists_in_workdir: bool
        exists_in_location_state: bool
        is_most_recent: bool

        def __init__(self, **kws):
            self.__dict__.update(kws)

        def __repr__(self):
            return 'St(' + ' '.join(
                f'{k}={v}' for k, v in
                self.__dict__.items()
            ) + ')'

    def get_file_stats(self) -> 'Dict[Path, Repository.FileStatus]':
        """
        Return a list of FileStatus() objects describing the status
        of all files in the repository.
        """
        files = self.repository_state.get_paths()
        logger.debug(f'files in repo: {files}')

        stats = {}
        for path in files:
            re = self.repository_state.get(path)
            assert re is not None
            le = self.location_states.get_file_state(self.id, path)

            f = Repository.FileStatus(
                path=path,
                exists_in_repository=True,
                maybe_modified=self.working_directory.file_maybe_modified(le),
                exists_in_workdir=(path in self.working_directory),
                exists_in_location_state=le.exists(),
                is_most_recent=(not le.exists() or le.digest == re.digest),
                )
            stats[path] = f

        logger.debug(f'wd files: {self.working_directory.get_filenames()}')
        wd_only_files = set(self.working_directory.get_filenames()) - set(files)
        logger.debug(f'wd only files: {wd_only_files}')
        for path in wd_only_files:
            f = Repository.FileStatus(
                path=path,
                exists_in_repository=False,
                maybe_modified=True,
                exists_in_workdir=True,
                exists_in_location_state=False,
                is_most_recent=True,
                )
            stats[path] = f

        return stats




