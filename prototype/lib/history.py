
import configuration
import json
import hashlib
import os
import os.path

class History:
    def __init__(self, repository):
        self.repository = repository

    def process_copy_notices(self):
        """
        Process all the copy notices in the repository (if any)
        into a commit and apply that.
        """
        pass

    def has_commit(self, commit_id):
        filepath = self.commit_dir(commit_id)
        return os.path.exists(filepath)
    
    def get_commit(self, commit_id):
        filepath = self.commit_dir(commit_id)
        with open(filepath, 'r') as f:
            r = json.load(f, object_hook = json_encoder.object_hook)
        return r
        
    def add_commit(self, c):
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
        #self.set_head(h)
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

    def set_head(self, hid):
        assert isinstance(hid, str)
        path = os.path.join(self.repository.harmony_dir(), 'HEAD')
        with open(path, 'w') as f:
            f.write(hid.strip())
    
    def get_head(self, subpath='HEAD'):
        path = self.repository.harmony_dir(subpath) #os.path.join(self.harmony_dir(), 'HEAD')
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            r = f.read().strip()
        return r


#  vim: set ts=4 sw=4 tw=78 expandtab :
