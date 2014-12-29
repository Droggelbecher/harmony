
from file_info import FileInfo
import json_encoder
import datetime
import logging

from commit_difference import Edit, Deletion, Rename, Creation

class Commit:
    # This is not exactly ISO 8601, but close.
    # Unfortunately datetime can't parse its own .isoformat() output
    # (d'oh!)
    datetime_format = '%Y-%m-%dT%H:%M:%S.%f'
    
    def __init__(self, repo = None):
        self.parents_ = set()
        self.files_ = {}
        self.by_content_id_ = {}
        if repo:
            self.repository_id = repo.id()
        else:
            self.repository_id = None
        self.created = datetime.datetime.utcnow()
        
    def add_files_from(self, commit):
        for fn in commit.get_filenames():
            fi = commit.get_file(fn)
            self.add_file(fn, fi)
        
    def get_parents(self):
        return self.parents_
    
    def add_parent(self, parent):
        assert isinstance(parent, str)
        self.parents_.add(parent)
        
    def set_parents(self, p):
        for par in p:
            assert isinstance(par, str)
            
        self.parents_ = list(p)
    
    def empty(self):
        return len(self.files_) == 0
    
    #
    # Serialization, Comparison
    # 
    
    def serialize(self):
        return {
            'creating_repository': self.repository_id,
            'parents': self.parents_,
            'files': self.files_,
            'created': self.created.strftime(Commit.datetime_format)
        }
    
    @staticmethod
    def deserialize(dct):
        r = Commit()
        r.repository_id = dct['creating_repository']
        r.parents_ = dct['parents']
        r.created = datetime.datetime.strptime(dct['created'], Commit.datetime_format)
        for fname, fi in dct['files'].items():
            r.add_file(fname, fi)
        return r
    
    def apply_change(self, change):
        if isinstance(change, Deletion):
            self.delete_file(change.old_filename)
        elif isinstance(change, Edit):
            self.edit_file(change.new_filename, change.new_fileinfo)
        elif isinstance(change, Rename):
            self.rename_file(change.old_filename, change.new_filename)
        elif isinstance(change, Creation):
            self.add_file(change.new_filename, change.new_fileinfo)
        else:
            logging.debug("dont know how to apply {}".format(change))
            assert False
    
    def add_file(self, relative_path, fi):
        # TODO: normalize relative path
        self.files_[relative_path] = fi
        if fi.content_id not in self.by_content_id_:
            self.by_content_id_[fi.content_id] = set()
        self.by_content_id_[fi.content_id].add(relative_path)
        
    def delete_file(self, relative_path):
        cid = self.files_[relative_path].content_id
        del self.files_[relative_path]
        self.by_content_id_[cid].discard(relative_path)
        
    def rename_file(self, from_, to):
        cid = self.files_[from_].content_id
        self.files_[to] = self.files[from_]
        del self.files[from_]
        self.by_content_id_[cid].discard(from_)
        self.by_content_id_[cid].add(to)
        
    def edit_file(self, filename, new_fileinfo):
        if filename in self.files_:
            fi = self.files_[filename]
            cid = fi.content_id
            if cid in self.by_content_id_[cid]:
                self.by_content_id_[cid].discard(filename)
            if len(self.by_content_id_[cid]) == 0:
                del self.by_content_id_[cid]
                
        self.files_[filename] = new_fileinfo
        new_cid = new_fileinfo.content_id
        if new_cid not in self.by_content_id_:
            self.by_content_id_[new_cid] = set()
        self.by_content_id_[new_cid].add(filename)
    
    def get_filenames(self):
        return self.files_.keys()
    
    def get_content_ids(self):
        return self.by_content_id_.keys()
    
    def get_file(self, relative_path):
        return self.files_.get(relative_path, None)
    
    def get_by_content_id(self, content_id):
        return self.by_content_id_.get(content_id, set()).copy()
    

json_encoder.register(Commit)

