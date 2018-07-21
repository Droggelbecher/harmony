
import logging
import os
from copy import deepcopy

from harmony.util import shortened_id
from harmony.repository_state import RepositoryState

logger = logging.getLogger(__name__)

def commit(local_location_id, working_directory, location_states, repository_state):
    """
    Scan the given working directory for changes and commit them to local
    state storage.
    That is, update location_states[local_location_id] with the
    new current file states (digests, "who has what?").
    Also update repository_state info ("who made which content decision in what
    order?")

    Parameters:

    local_location_id:
        ID of the location that is considered local (i.e. the one that belongs
        to the working_directory instance)

    working_directory:
        WorkingDirectory instance representing the local working directory.

    location_states:
        LocationStates instance representing the local location state storage.
        Will (possibly) be modified.

    repository_state:
        RepositoryState instance representing the local repository state
        storage. Will (possibly) be modified.

    return:
        True iff any change was recorded.
    """

    id_ = local_location_id
    short_id = shortened_id(id_)

    paths = set(working_directory.get_filenames()) \
            | set(location_states.get_all_paths(id_))


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
        path: working_directory.scan_file(path)
        for path in paths
        if working_directory.file_maybe_modified(
            location_states.get_file_state(id_, path)
        )
    }

    location_state_cache = {
        path: location_states.get_file_state(id_, path)
        for path in paths
    }

    any_change = False
    for path in paths:
        if path not in wd_states:
            logger.debug('{} not in workdir: {}'.format(short_id, path))
            continue

        file_state = location_state_cache[path]
        new_file_state = wd_states[path]
        changed = location_states.update_file_state(id_, new_file_state)
        if not changed:
            logger.debug('{} not actually changed: {}'.format(short_id, path))
            continue

        any_change = True

        # If the file vanished but a new one with the same digest
        # popped up, consider that a rename.
        # Rename means, the old file is WIPEd (instead of just
        # locally removed) and the new file is added as usual
        if not new_file_state.exists():
            logger.debug('{} vanished'.format(new_file_state.path))

            # Iterate over paths to find a possible rename target
            for path2 in paths:
                # Rename to itself does not make sense
                # Rename to a file that has not changed (or better: just appeared) does not make sense
                if path2 == path or path2 not in wd_states:
                    continue

                path2_state = location_state_cache[path2]
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

        repository_state.update_file_state(
            new_file_state,
            id_,
            location_states.get_clock(id_) + 1,
        )
        logger.debug('{} committed: {} clk={}'.format(short_id, new_file_state.path, location_states.get_clock(id_) + 1))

    return any_change


def merge(local_state, remote_state, merger_id):
    """
    Merge two repository states ('local' and 'remote') into a common state if
    possible, auto-detecting if a change only happened on one side and
    propagating those changes.
    For cases in which a file was changed on both sides, return details of the
    conflict.

    local_state:
        RepositoryState() instance that reflects the local repository state.
    remote_state:
        RepositoryState() instance that reflects the remote repository state.
    merger_id:
        ID of the repository conducting the merge (assumed to correspond
        to the 'local' repository)
    return:
        A pair (conflicts, merged).
        $conflicts is a dictonary of the form { path: (local_entry, remote_entry),
        ... } whereas $path denotes the path of a file in conflict and $local_entry
        and $remote_entry refer to the RepositoryState.Entry instances for that
        file that are in conflict. 
        $merged is a newly created RepositoryState instance with selected merged
        repository states. 
        If $conflicts is empty, $merged covers all files present either locally or
        remotely.
    """
    local_paths = set(local_state.get_paths())
    remote_paths = set(remote_state.get_paths())

    merged = RepositoryState(None)
    conflicts = {}

    for p in local_paths - remote_paths:
        merged[p] = local_state[p]

    for p in remote_paths - local_paths:
        merged[p] = remote_state[p]


    # conflicts can only arise in paths that are specified in both state
    # files
    paths = set(local_state.get_paths()) & set(remote_state.get_paths())

    for path in paths:
        local = local_state[path]
        remote = remote_state[path]

        c = local.clock.compare(remote.clock)
        if c is None:
            if local.contents_different(remote):
                logger.debug('merge: {} in conflict: {} <-> {}'.format(
                    path, local.clock, remote.clock
                ))
                conflicts[path] = (local, remote)
            else:
                logger.debug('merge: {} automerged (same content)'.format(path))
                m = deepcopy(local)
                m.clock.update(remote.clock)
                m.clock.increase(merger_id)
                merged[path] = m

        elif c < 0:
            logger.debug('merge: {} newer on remote'.format(path))
            merged[path] = remote

        else: # c >= 0:
            logger.debug('merge: {} same version or newer on local'.format(path))
            merged[path] = local

    return conflicts, merged



def auto_rename(working_directory, repository_state):
    from harmony.working_directory import WorkingDirectory

    assert isinstance(working_directory, WorkingDirectory)
    """
    Apply automatic renaming in the given working_directory.
    That is, if working dir contains files that are WIPEd in $repository_state but
    are present under a different name, automatically rename those to obtain
    the repository file at a low cost.

    Repository.commit() should be called after calling this to commit the
    changes to the working directory.

    precondition: WD clean
    """

    # Automatically apply auto-renaming
    # Auto-renaming
    # -------------
    # 1. Find any files $A with a WIPE entry.
    # 2. Compute/get their digest (from location state)
    # 3. Find a non-wiped file $B in repo that does not exist in the WD
    # 4. Rename $A to $B

    for path, entry in repository_state.files.items():
        logger.debug('auto_rename: {}: path={} wipe={} in_wd={}'.format(path, entry.path, entry.wipe, (entry.path in working_directory)))
        if entry.wipe and (entry.path in working_directory):
            possible_targets = {
                e.path for e in repository_state.files.values()
                if e.path != path and e.digest == entry.digest and not e.wipe
            }
            logger.info(
                '{} could be auto-renamed to any of {}'.format(
                    path, possible_targets
                )
            )
            if possible_targets:
                (working_directory.path / path).rename(working_directory.path / possible_targets.pop())



