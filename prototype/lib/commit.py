
from file_info import FileInfo
import json_encoder
import datetime
import logging
import copy

from commit_difference import Edit, Deletion, Rename, Creation

class Commit:
    """
    Commit invariants:
    - If a commit holds a filename/content_id combination, the according
      FileInfo lists all sources (repositories) that hold this
      filename/content_id combination
    - In that case this content is also the "newest" content for that filename
      for the branch identified by the commit


    {
        'created': '12-13-14...',
        'creating_repository': '1234-5...',

        'clock': {
            '1234-5678...': 10,
            '1122-3344...': 2,
        },

        # path -> { repo -> content_id & co. }
        'files': {
            'path/to/file': {
                'default_version': 'sha256:1234....',
                'versions': {
                    'sha256:1234': {
                        '1234-567...': {
                            'modified': '12-34-56...',
                            'observed': '12-34-56',
                        },
                        ...
                    ]
                }
            }
        },

        # content_id -> { repo, path }
        #'contents': {
            #'sha256:1234...': {
                    #{ 'repository': '12345...', 'path': 'fobbar/baz.txt' },
                    #{ 'repository': '67890...', 'path': 'fobbar/baz.txt' },
                    #{ 'repository': '67890...', 'path': 'fobbar/blub.txt' },
            #}
        #}
    }

    """

    # This is not exactly ISO 8601, but close.
    # Unfortunately datetime can't parse its own .isoformat() output
    # (d'oh!)
    datetime_format = '%Y-%m-%dT%H:%M:%S.%f'
    
    def __init__(self, repo = None):
        self.parents_ = {}
        self.files_ = {}
        self.clock_ = {}
        self.by_content_id_ = {}
        if repo is not None:
            self.repository_id = repo.id()
            self.created = datetime.datetime.utcnow()
            self.update_clock()
    
    def copy(other, repository_id = None):
        self = Commit()
        self.parents_ = {} #other.parents_.copy()
        self.files_ = copy.deepcopy(other.files_)
        self.clock_ = copy.deepcopy(other.clock_)
        self.by_content_id_ = copy.deepcopy(other.by_content_id_)
        self.repository_id = repository_id or other.repository_id
        self.created = datetime.datetime.utcnow()
        self.update_clock()
        return self

    def erase_source(self, repo_id):
        for relfn in self.get_filenames():
            versions = tuple(self.get_file_versions(relfn).keys())
            for cid in versions:
                e = self.get_file_version(relfn, cid)
                if repo_id in e:
                    del e[repo_id]
                    self.set_file_version(relfn, cid, e)


        
    #def add_files_from(self, commit):
        #for fn in commit.get_filenames():
            #fi = commit.get_file(fn)
            #self.add_file(fn, fi)
        
    def get_parents(self):
        return self.parents_
    
    def add_parent(self, parent):
        assert isinstance(parent, dict)
        assert len(parent) == 1
        assert isinstance(list(parent.keys())[0], str)
        assert isinstance(list(parent.values())[0], Commit)

        self.parents_.update(parent)
        self.update_clock()
        
    def set_parents(self, parents):
        assert isinstance(parents, dict)

        if len(parents) > 0:
            assert isinstance(list(parents.keys())[0], str)
            assert isinstance(list(parents.values())[0], Commit)
            
        self.parents_ = parents.copy()
        self.update_clock()

    def update_clock(self):
        self.clock_ = {}
        for pid, p in self.parents_.items():
            c = p.clock_
            for repo_id, clock_value in c.items():
                if self.clock_.get(repo_id, 0) < clock_value:
                    self.clock_[repo_id] = clock_value
        self.clock_[self.repository_id] = self.clock_.get(self.repository_id, 0) + 1

    def compare_clock(self, other):
        """
        @return (result, individual_results)
        
        result is one of (-1, 0, 1, None).
        -1   -> This commit is a strict predecessor of other
        0    -> The commits have the same clock values (and should thus be identical)
        1    -> This commit is a successor of other
        None -> The commits are not ordered, i.e. clocks of different
            repositories have advanced without merging.

        individual_results is a dict remote_id => result
        """
        keys = set(self.clock_.keys()).union(other.clock_.keys())
        order = 0
        individual_results = dict()

        for k in keys:
            v_self = self.clock_.get(k, 0)
            v_other = other.clock_.get(k, 0)
            c = -1 if v_self < v_other else (1 if v_self > v_other else 0)
            individual_results[k] = c

            if order == 0: # and c != 0:
                # So far, both sides were equal,
                # this item defines the order
                order = c
            elif -c == order:
                # Found a contradiction to the current order
                # assumption, so they are not ordered
                order = None
                break
        return (order, individual_results)

            
    
    def empty(self):
        return len(self.files_) == 0
    
    #
    # Serialization, Comparison
    # 
    
    def serialize(self):
        return {
            'creating_repository': self.repository_id,
            'created': self.created.strftime(Commit.datetime_format),
            'parents': list(self.parents_.keys()),
            'files': self.files_,
            'clock': self.clock_,
        }
    
    @staticmethod
    def deserialize(dct):
        r = Commit()
        r.repository_id = dct['creating_repository']
        r.parents_ = dict((k, None) for k in dct['parents'])
        r.created = datetime.datetime.strptime(dct['created'], Commit.datetime_format)
        r.files_ = dct['files']
        r.clock_ = dct['clock']
        return r

    def has_file(self, relfn):
        return relfn in self.files_

    def get_filenames(self):
        return self.files_.keys()

    def get_filenames_for_source(self, src):
        for fn in self.get_filenames():
            try: self.get_file_content_by_repo(fn, src)
            except ValueError:
                pass
            else:
                yield fn

    def get_file_entry(self, relfn):
        return self.files_.get(relfn, {})

    def get_file_versions(self, relfn):
        return self.get_file_entry(relfn).get('versions', {})

    def get_file_version(self, relfn, cid):
        return self.get_file_versions(relfn).get(cid, {})

    def get_file_content_by_repo(self, relfn, repo_id):
        d = self.get_file_versions(relfn)
        for k, v in d.items():
            if repo_id in v.keys(): return k
        raise ValueError('Repo {} not found in sources for {}'.format(repo_id, relfn))

    def set_file_version(self, relfn, cid, d):
        dct = self.files_ \
                    .setdefault(relfn, {}) \
                    .setdefault('versions', {})

        if not d:
            if cid in dct:
                del dct[cid]
        else:
            dct[cid] = d.copy()

    def add_source(self, relfn, cid, repo_id):
        e = self.get_file_version(relfn, cid)
        e[repo_id] = { 'modified': None, 'observed': None }
        self.set_file_version(relfn, cid, e)

    def get_repos_providing(self, relfn, cid):
        return self.get_file_versions(relfn).get(cid, {}).keys()

    def get_default_version(self, relfn):
        return self.get_file_entry(relfn).get('default_version', None)

    def set_default_version(self, relfn, cid):
        self.files_.setdefault(relfn, {})['default_version'] = cid

    #def apply_change(self, change):
        #if isinstance(change, Deletion):
            #self.delete_file(change.old_filename)
        #elif isinstance(change, Edit):
            #self.edit_file(change.new_filename, change.new_fileinfo)
        #elif isinstance(change, Rename):
            #self.rename_file(change.old_filename, change.new_filename)
        #elif isinstance(change, Creation):
            #self.add_file(change.new_filename, change.new_fileinfo)
        #else:
            #logging.debug("dont know how to apply {}".format(change))
            #assert False
    
    #def add_file(self, relative_path, fi):
        ## TODO: normalize relative path
        #self.files_[relative_path] = fi
        #if fi.content_id not in self.by_content_id_:
            #self.by_content_id_[fi.content_id] = set()
        #self.by_content_id_[fi.content_id].add(relative_path)
        
    #def delete_file(self, relative_path):
        #cid = self.files_[relative_path].content_id
        #del self.files_[relative_path]
        #self.by_content_id_[cid].discard(relative_path)
        
    #def rename_file(self, from_, to):
        #cid = self.files_[from_].content_id
        #self.files_[to] = self.files[from_]
        #del self.files[from_]
        #self.by_content_id_[cid].discard(from_)
        #self.by_content_id_[cid].add(to)
        
    #def edit_file(self, filename, new_fileinfo):
        #if filename in self.files_:
            #fi = self.files_[filename]
            #cid = fi.content_id
            #if cid in self.by_content_id_[cid]:
                #self.by_content_id_[cid].discard(filename)
            #if len(self.by_content_id_[cid]) == 0:
                #del self.by_content_id_[cid]
                
        #self.files_[filename] = new_fileinfo
        #new_cid = new_fileinfo.content_id
        #if new_cid not in self.by_content_id_:
            #self.by_content_id_[new_cid] = set()
        #self.by_content_id_[new_cid].add(filename)
    
    #def get_filenames(self):
        #return self.files_.keys()
    
    #def get_content_ids(self):
        #return self.by_content_id_.keys()
    
    # TODO: Implement getters and a useful data structure for storage once we
    # know how we want to access it


    #def get_file(self, relative_path):
        #return self.files_.get(relative_path, None)
    
    #def get_by_content_id(self, content_id):
        #return self.by_content_id_.get(content_id, set()).copy()
    

json_encoder.register(Commit)

