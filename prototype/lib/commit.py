
from file_info import FileInfo
import json_encoder
import datetime
import logging

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
        if repo:
            self.repository_id = repo.id()
        else:
            self.repository_id = None
        self.created = datetime.datetime.utcnow()
        self.update_clock()
        
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

    def get_file_entry(self, relfn):
        return self.files_.get(relfn, {})

    def get_file_versions(self, relfn):
        return self.get_file_entry(relfn).get('versions', {})

    def get_file_version(self, relfn, cid):
        return self.get_file_versions(relfn).get(cid, {})

    def set_file_version(self, relfn, cid, d):
        self.files_ \
                .setdefault(relfn, {}) \
                .setdefault('versions', {}) \
                [cid] = d.copy()

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

