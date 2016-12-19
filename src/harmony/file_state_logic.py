
import logging
from harmony.util import shortened_id

logger = logging.getLogger(__name__)

def commit(
    local_location_id,
    working_directory,
    location_states,
    repository_state,
):
    """
    Scan the given working directory for changes and commit those to local
    state storage.
    That is, update location_states[local_location_id] with the
    new current file states (digests, "who has what?").
    Also update repository_state info ("who made which content decision in what
    order?")

    Parameters:

    local_location_id: ID of the location that is considered local (i.e. the
        one that belongs to the working_directory instance)

    working_directory: WorkingDirectory instance representing the local working
        directory.

    location_states: LocationStates instance representing the local location
        state storage. Will (possibly) be modified.

    repository_state: RepositoryState instance representing the local
        repository state storage. Will (possibly) be modified.
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
        path: working_directory.generate_file_state(path)
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

        if path in wd_states:
            file_state = location_state_cache[path]
            new_file_state = wd_states[path]
            changed = location_states.update_file_state(id_, new_file_state)
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
            else:
                logger.debug('{} not actually changed: {}'.format(short_id, path))
        else:
            logger.debug('{} not changed: {}'.format(short_id, path))

    return any_change

