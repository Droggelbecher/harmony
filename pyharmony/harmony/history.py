
import os
import os.path
import hashlib
import datetime
import logging
from harmony import protocols

from harmony.commit import Commit
from harmony import serialization

class History:

    COMMITS_SUBDIR = 'commits'

    LOCAL_HEAD_FILE = 'HEAD'
    MERGE_HEAD_FILE = 'MERGE_HEAD'
    REMOTE_HEADS_SUBDIR = 'remote-heads'

    @classmethod
    def init(class_, harmony_directory):
        """
        Create a new history, within the given harmony directory.
        """
        commits_directory = os.path.join(harmony_directory, class_.COMMITS_SUBDIR)
        os.mkdir(commits_directory)
        remote_heads_directory = os.path.join(harmony_directory, class_.REMOTE_HEADS_SUBDIR)
        os.mkdir(remote_heads_directory)

        h = History(harmony_directory)
        return h

    @classmethod
    def load(class_, harmony_directory):
        h = History(harmony_directory)
        return h

    def __init__(self, harmony_directory):
        self.harmony_directory = harmony_directory
        self.commits_directory = os.path.join(harmony_directory, History.COMMITS_SUBDIR)
        self.remote_heads_directory = os.path.join(harmony_directory, History.REMOTE_HEADS_SUBDIR)


    def get_head_id(self):
        local_head_file = os.path.join(self.harmony_directory, History.LOCAL_HEAD_FILE)
        if os.path.exists(local_head_file):
            with open(local_head_file, 'r') as f:
                return f.read()
        return None

    def set_head_id(self, head_id):
        with open(os.path.join(self.harmony_directory, History.LOCAL_HEAD_FILE), 'w') as f:
            f.write(head_id)

    def get_merge_head_id(self):
        merge_head_file = os.path.join(self.harmony_directory, History.MERGE_HEAD_FILE)
        if os.path.exists(merge_head_file):
            with open(merge_head_file, 'r') as f:
                return f.read()
        return None

    def set_merge_head_id(self, head_id):
        with open(os.path.join(self.harmony_directory, History.MERGE_HEAD_FILE), 'w') as f:
            f.write(head_id)

    def unset_merge_head_id(self):
        os.remove(os.path.join(self.harmony_directory, History.MERGE_HEAD_FILE))

    def get_head_ids(self):
        s = set()
        my = self.get_head_id()
        if my is not None: s.add(my)

        merge = self.get_merge_head_id()
        if merge is not None: s.add(merge)

        return s

    def get_remote_head_ids(self):
        heads = set()
        for filename in os.listdir(self.remote_heads_directory):
            with open(os.path.join(self.remote_heads_directory, filename), 'r') as f:
                heads.add(f.read().strip())
        return list(heads)


    def create_commit(self):
        """
        @return New commit with parents set to local heads.
        """

        heads = self.get_head_ids()
        c = Commit(parents = heads)
        return c

    def add_head(self, c):
        """
        Add commit c to history as new local head.
        """
        commit_id = self.write_commit(c)
        self.set_head_id(commit_id)

    def get_commit(self, digest):
        fn = os.path.join(self.commits_directory, digest)
        commit_data = serialization.read(fn)

        c = Commit()
        c.parents = commit_data['parents']
        c.created = datetime.datetime.strptime(commit_data['created'], Commit.DATETIME_FORMAT)
        c.files = commit_data['files']
        c.repositories = commit_data['repositories']
        return c

    def get_head(self):
        head_id = self.get_head_id()
        head = None
        if head_id is not None:
            head = self.get_commit(head_id)
        return head


    def write_commit(self, c):
        d = {
            'parents': sorted(list(c.parents)),
            'created': c.created.strftime(Commit.DATETIME_FORMAT),
            'files': c.files,
            'repositories': c.repositories,
        }
        commit_string = serialization.dump(d)

        digest = hashlib.sha1(commit_string.encode('utf-8')).hexdigest()
        with open(os.path.join(self.commits_directory, digest), 'w') as f:
            f.write(commit_string)
        return digest

    def find_remotes(self, remote_specs):
        """
        Given a number of remote specs, return URIs for all remotes that could
        be identified.

        """

        # This safeguards againsts accidentially passing a single remote spec
        assert isinstance(remote_specs, list) \
                or isinstance(remote_specs, tuple)


        # TODO: fix this not to expect URIs in history but rather look up
        # self.remotes
        
        head = self.get_head()
        remotes = []

        if len(remote_specs) == 0:
            for uuid, remote_desc in head.repositories.items():
                remotes.append(remote_desc['uri'])

        else:
            for rspec in remote_specs:
                # TODO:
                #
                # * check whether spec is a UUID or UNIQUE prefix of a UUID of
                #   a known repository
                
                if head is not None:
                    found_remotes = set()

                    for uuid, remote_desc in head.repositories.items():
                        if uuid.startswith(rspec):
                            found_remotes.add(remote_desc)

                    if len(found_remotes) == 1:
                        remotes.append(found_remotes.pop()['uri'])
                        continue # next rspec
                
                # * check whether spec is the name of a known repository
                #

                    for uuid, remote in head.repositories.items():
                        if rspec == remote['name']:
                            remotes.append(remote['uri'])
                            continue
                
                # * check whether spec is URI of a repository (not necessarily
                #   known!).
                #   for this, check all the protocols
                #

                connection = protocols.connect(rspec)
                assert connection is not None
                remotes.append(rspec)
                continue

        return remotes

    def find_least_common_ancestor(self, id_a, id_b):
        #a = self.get_commit(id_a)
        #b = self.get_commit(id_b)

        # find ancestors of a

        ancestors_a = set()
        ancestors_a_todo = set([id_a])

        while ancestors_a_todo:
            cid = ancestors_a_todo.pop()
            ancestors_a.add(cid)

            c = self.get_commit(cid)
            ancestors_a_todo.update(set(c.parents).difference(ancestors_a))


        ancestors_b = set()
        ancestors_b_todo = [id_b]

        # now find ancestors of b with BFS, first encountered ancestor
        # of a is an LCA
        while ancestors_b_todo:
            cid = ancestors_b_todo[0]

            if cid in ancestors_a:
                return cid

            ancestors_b_todo = ancestors_b_todo[1:]
            ancestors_b.add(cid)

            c = self.get_commit(cid)

            # append c.parents that are not in the list
            # appending leads to bfs, prepending would be dfs
            for p in c.parents:
                if p not in ancestors_b_todo and p not in ancestors_b:
                    ancestors_b_todo.append(p)

        return None
    

    def merge_remote(self, remote_id):
        """
        Given a remote_id, merge the HEAD of that remote.

        Preconditions:
            - remote_id is a valid, locally known remote id
            - The remote HEAD and all commits are locally available.

        @return A tuple (commit, conflicts) where commit is None or a merging
            commit and conflicts is a dictionary of the form
            { filename: (digest_local, digest_remote) }

        Postconditions:
            The following cases can occur w.r.t to return value:

            1. commit is None, conflicts == {}
                The merge operation was trivial (e.g. a fast forward).
                HEAD may have been set to a preexisting commit.
                No additional commit is necessary in this case.

            2. commit is not None, conflicts == {}
                commit can be applied as-is as new HEAD (e.g. by calling
                add_head(commit))

            3. commit is not None, conflicts != {}
                commit is in undefined state for all filenames in
                conflicts.keys().
                Execute
                commit.update_file(filename, digest)
                for each of these filenames. digest should be one of the
                elements of the 2-tuple conflicts[filename].
                After this, commit can be passed e.g. to add_head().
                If commit is not fixed as described above, the result is
                undefined.
        """


        #
        # Preconditions
        #
        assert remote_id is not None

        conflicts = {}

        #
        # Get remote HEAD
        #

        remote_head_filename = os.path.join(self.remote_heads_directory, remote_id)
        if not os.path.exists(remote_head_filename):
            # If remote head ID is not known assume it is because
            # thre is no remote HEAD yet.
            # In that case there are also ne no remote commits and
            # thus merging is a no-op.
            logging.info('empty remote, nothing to update.')
            return None, conflicts

        with open(remote_head_filename, 'r') as f:
            remote_head_id = f.read()

        #
        # Make it the merge head
        #

        self.set_merge_head_id(remote_head_id)

        local_head_id = self.get_head_id()

        if local_head_id is None:
            logging.info('cloning.')
            # We dont have a head yet, that makes merging quite easy
            self.set_head_id(remote_head_id)
            self.unset_merge_head_id()
            return None, conflicts

        lca_id = self.find_least_common_ancestor(local_head_id, remote_head_id)

        if lca_id == local_head_id:
            # Fast-forward to remote head
            logging.info('fast-forward.')
            self.set_head_id(remote_head_id)
            self.unset_merge_head_id()
            return None, conflicts

        elif lca_id == remote_head_id:
            logging.info('up-to-date.')
            # remote end is behind, do nothing
            return None, conflicts

        elif lca_id is None:
            raise ConsistencyException('Repositories not related.')

        else:
            lca = self.get_commit(lca_id)
            local = self.get_commit(local_head_id)
            remote = self.get_commit(remote_head_id)

            c = self.create_commit()

            c.update_repositories(remote)
            c.update_repositories(local)
            c.inherit_files(lca)

            filenames = set(lca.files.keys())
            filenames.update(set(local.files.keys()))
            filenames.update(set(remote.files.keys()))

            # Now look for conflicting file versions.
            # There are several cases that can occur:
           
            for filename in filenames:
                d_lca = lca.get_file(filename)
                d_local = local.get_file(filename)
                d_remote = remote.get_file(filename)

            # 0. files existing only in lca
            #    -> keep (we already have those due to inherit_files(lca)

            # 1. files existing only in local and possibly lca with same version
            #    -> keep (we already have those due to inherit_files(lca)

            # 2. files existing only in remote and possibly lca with same version
            #    -> keep (we already have those due to inherit_files(lca)

            # 7. files present in lca and a nonempty subset of {local, remote}
            #    with the same version
            #    -> keep (we already have those due to inherit_files(lca)

            # 6. files added in both local and remote with the same digest
            #    -> either version is fine
                if d_local is not None \
                        and d_local == d_remote \
                        and d_lca is None:
                    c.update_file(filename, d_local)

            # 3. files changed in local and deleted or not-changed in remote
            #    -> local version

                elif (d_local is not None and d_local != d_lca and
                        (d_remote is None or d_remote == d_lca)):
                    c.update_file(filename, d_local)

            # 4. files changed in remote and deleted or not-changed in local
            #    -> remote version

                elif (d_remote is not None and d_remote != d_lca and
                        (d_local is None or d_local == d_lca)):
                    c.update_file(filename, d_remote)

            # 5. files different in local and remote, with lca having either
            #    a third version or none at all
            #    -> CONFLICT
                
                elif d_remote is not None \
                        and d_local is not None \
                        and d_remote != d_local \
                        and (d_lca != d_local and d_lca != d_remote): # includes the case d_lca == None

                    conflicts[filename] = (d_local, d_remote)

        return c, conflicts

    def compute_graph_layout(self, starting_commit):

        lines = []

        def add_commit(cid, lines):
            c = self.get_commit(cid)

            pickup_paths = []
            for parent in c.parents:
                i = find_commit(parent, lines)
                if i is not None:
                    pickup_paths.append(add_path(lines[i:]))
                add_commit(parent, lines)

            #for p in pick_paths:
                #add_pickup(p, lines)
            lines.append({'paths': set(), 'commit_id': cid, 'commit': c, 'pickup_paths': pickup_paths})

        def add_path(lines):
            path = object()
            for line in lines:
                #if 'paths' not in line:
                    #line['paths'] = set()
                line['paths'].add(path)

        def find_commit(cid, lines):
            for i, line in enumerate(lines):
                if 'commit' in line and line['commit_id'] == cid:
                    return i
            return None

        add_commit(starting_commit, lines)

        return lines


    def format_log(self, starting_commit=None):
        if starting_commit is None:
            starting_commit = self.get_head_id()

        lines = self.compute_graph_layout(starting_commit)

        for line in lines:
            print("{} -- {} p's={}".format(line['paths'], line['commit_id'],
            line['commit'].parents))



