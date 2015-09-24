
import os
import os.path
import hashlib
import datetime
from harmony import protocols

from harmony.commit import Commit
from harmony import serialization

class History:

    COMMITS_SUBDIR = 'commits'

    LOCAL_HEAD_FILE = 'HEAD'
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

    def get_local_head_id(self):
        local_head_file = os.path.join(self.harmony_directory, History.LOCAL_HEAD_FILE)
        if os.path.exists(local_head_file):
            with open(local_head_file, 'r') as f:
                return f.read()
        return None

    def get_heads(self):
        # TODO: read local head file
        # TODO: read remote head files

        heads = set()

        local_head_file = os.path.join(self.harmony_directory, History.LOCAL_HEAD_FILE)
        if os.path.exists(local_head_file):
            with open(local_head_file, 'r') as f:
                heads.add(f.read().strip())

        for filename in os.listdir(self.remote_heads_directory):
            with open(filename, 'r') as f:
                heads.add(f.read().strip())
        return list(heads)


    def create_commit(self):
        """
        @return New commit with parents set to local heads.
        """

        heads = self.get_heads()
        c = Commit(parents = heads)
        return c

    def add_head(self, c):
        """
        Add commit c to history as new local head.
        """
        commit_id = self.write_commit(c)
        self.write_head(commit_id)

    def get_commit(self, digest):
        fn = os.path.join(self.commits_directory, digest)
        commit_data = serialization.read(fn)

        c = Commit()
        c.parents = commit_data['parents']
        c.created = datetime.datetime.strptime(commit_data['created'], Commit.DATETIME_FORMAT)
        c.files = commit_data['files']
        c.repositories = commit_data['repositories']
        return c

    def get_local_head(self):
        head_id = self.get_local_head_id()
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

    def write_head(self, head_id):
        with open(os.path.join(self.harmony_directory, History.LOCAL_HEAD_FILE), 'w') as f:
            f.write(head_id)

    def find_remotes(self, remote_specs):
        """
        Given a number of remote specs, return URIs for all remotes that could
        be identified.

        """

        # TODO: fix this not to expect URIs in history but rather look up
        # self.remotes
        
        head = self.get_local_head()
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
                print("rspec=", rspec)
                assert connection is not None
                remotes.append(rspec)
                continue

        return remotes

    def find_least_common_ancestor(self, id_a, id_b):
        a = self.get_commit(id_a)
        b = self.get_commit(id_b)

        # find ancestors of a

        ancestors_a = set()
        ancestors_a_todo = set(a)

        while ancestors_a_todo:
            c = ancestors_a_todo.pop()
            ancestors_a.add(c)
            ancestors_a_todo.update(c.parents.difference(ancestors_a))


        ancestors_b = set()
        ancestors_b_todo = set(b)

        # now find ancestors of b with BFS, first encountered ancestor
        # of a is an LCA
        while ancestors_b_todo:
            c = ancestors_b_todo[0]

            if c in ancestors_a:
                return c

            ancestors_b_todo = ancestors_b_todo[1:]
            ancestors_b.add(c)

            # append c.parents that are not in the list
            # appending leads to bfs, prepending would be dfs
            for p in c.parents:
                if p not in ancestors_b_todo and p not in ancestors_b:
                    ancestors_b_todo.append(p)

        return None
    

    def merge_remote(self, remote_id):
        assert self.remote_heads_directory is not None
        assert remote_id is not None

        conflicts = {}

        with open(os.path.join(self.remote_heads_directory, remote_id), 'r') as f:
            remote_head_id = f.read()
        
        local_head_id = self.get_local_head_id()

        if local_head_id is None:
            # We dont have a head yet, that makes merging quite easy
            # TODO: We still have to add a new commit with the new file list!
            self.write_head(remote_head_id)
            return

        assert local_head_id is not None
        assert remote_head_id is not None

        lca_id = self.find_least_common_ancestor(local_head_id, remote_head_id)

        if lca_id == local_head_id:
            # Fast-forward.
            self.write_head(remote_head_id)
            return

        elif lca_id == remote_head_id:
            # remote end is behind, do nothing
            pass

        elif lca_id is None:
            assert False

        else:
            lca = self.get_commit(lca_id)
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

        return conflicts


