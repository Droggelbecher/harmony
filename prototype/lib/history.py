
import configuration
import json
import json_encoder
import hashlib
import os
import os.path
import logging
from commit import Commit

class History:
    def __init__(self, repository):
        self.repository = repository

    def commit_dir(self, subpath):
        return self.repository.commit_dir(subpath)

    def has_commit(self, commit_id):
        filepath = self.commit_dir(commit_id)
        return os.path.exists(filepath)
    
    def get_commit(self, commit_id):
        assert isinstance(commit_id, str)

        filepath = self.commit_dir(commit_id)
        with open(filepath, 'r') as f:
            r = json.load(f, object_hook = json_encoder.object_hook)
        return r

    def create_commit(self, on_top = False, copy = True):
        if on_top:
            hid = self.get_head_id()
            if hid is not None:
                head = self.get_commit(hid)
                assert head is not None
                if copy:
                    c = head.copy(repository_id = self.repository.id())
                    c.add_parent({hid: head})
                    return c

        logging.warning('Creating initial commit')
        c = Commit(self.repository)
        return c
        
    def save_commit(self, c):
        # Write a commit with the description c to disk and return its hash
        s = json.dumps(c,
                cls = json_encoder.JSONEncoder,
                separators = (',', ': '),
                indent = 2,
                sort_keys = True,
        )
        h = hashlib.sha256(s.encode('utf-8')).hexdigest()
        filepath = self.commit_dir(h)
        with open(filepath, 'w') as f:
            f.write(s)
        return h

    def get_log(self):
        history = []
        c = self.get_head_id()
        branches = set([(c, self.get_commit(c))])
        
        while branches:
            # find next (in terms of date/time) commit
            max_commit = None
            max_commit_id = None
            for cid, b in branches:
                if max_commit is None or b.created > max_commit.created:
                    max_commit = b
                    max_commit_id = cid
            branches.discard((max_commit_id, max_commit))
            #history.append((max_commit_id, max_commit))
            yield (max_commit_id, max_commit)
            
            for cid in max_commit.get_parents():
                branches.add((cid, self.get_commit(cid)))
        return history

    def set_head_id(self, hid):
        assert isinstance(hid, str)
        path = os.path.join(self.repository.harmony_dir(), 'HEAD')
        with open(path, 'w') as f:
            f.write(hid.strip())
    
    def get_head_id(self, subpath='HEAD'):
        path = self.repository.harmony_dir(subpath) #os.path.join(self.harmony_dir(), 'HEAD')
        if not os.path.exists(path):
            logging.warning("'{}' does not exist.".format(path))
            return None
        with open(path, 'r') as f:
            r = f.read().strip()
        return r

    def get_head(self):
        return self.get_commit(self.get_head_id())


#  vim: set ts=4 sw=4 tw=78 expandtab :