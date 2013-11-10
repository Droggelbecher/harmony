
from file_info import FileInfo
import json_encoder
import datetime

from commit_difference import Edit, Deletion, Rename, Creation

class Commit:
	# This is not exactly ISO 8601, but close.
	# Unfortunately datetime can't parse its own .isoformat() output
	# (d'oh!)
	datetime_format = '%Y-%m-%dT%H:%M:%S.%f'
	
	def __init__(self, repo = None):
		self.parents = set()
		self.files_ = {}
		self.by_content_id_ = {}
		if repo:
			self.repository_id = repo.get_repository_id()
		else:
			self.repository_id = None
		self.created = datetime.datetime.utcnow()
		
	def add_parent(self, parent):
		self.parents.add(parent)
	
	def empty(self):
		return len(self.files_) == 0
	
	#
	# Serialization, Comparison
	# 
	
	def serialize(self):
		return {
			'creating_repository': self.repository_id,
			'parents': self.parents,
			'files': self.files_,
			'created': self.created.strftime(Commit.datetime_format)
		}
	
	@staticmethod
	def deserialize(dct):
		r = Commit()
		r.repository_id = dct['creating_repository']
		r.parents = dct['parents']
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
			self.add_file(change.new_filename, change, new_fileinfo)
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
		
	
	def get_filenames(self):
		return self.files_.keys()
	
	def get_content_ids(self):
		return self.by_content_id_.keys()
	
	def get_file(self, relative_path):
		return self.files_.get(relative_path, None)
	
	def get_by_content_id(self, content_id):
		return self.by_content_id_.get(content_id, None).copy()
	
	def __lca(self, other):
		"""
		Return lowest common ancestor.
		"""
		if self == other: return self
		
		ancestors_self = set()
		open_self = set([self])
		
		ancestors_other = set()
		open_other = set([other])
		
		while open_self or open_other:
			new = set()
			for p in open_self:
				if p in ancestors_other: return p
				new.update(p.parents)
			ancestors_self.update(open_self)
			open_self = new
			
			new = set()
			for p in open_other:
				if p in ancestors_self: return p
				new.update(p.parents)
			ancestors_other.update(open_other)
			open_other = new
		return None
	
	def __is_ancestor(self, other):
		return self.lca(other) == self
	
	def __merge(self, other, conflict_resolutions = {}):
		
		# Is this a fast-forward?
		if self.is_ancestor(other): return other.copy(), set()
		if other.is_ancestor(self): return self.copy(), set()
		
		# Non-trivial merge
		r = Commit()
		r.parents = (self, other)
		conflicts = set()
		
		filenames = set(self.files_.keys()).union(set(other.files_.keys()))
		
		for filename in filenames:
			if filename not in self.files_:
				r.files_[filename] = other.files_[filename].copy()
				
			elif filename not in other.files_:
				r.files_[filename] = self.files_[filename].copy()
				
			else:
				here = self.files_[filename]
				there = other.files_[filename]
				if here.content_id == there.content_id:
					r.files_[filename] = here.copy()
					r.files_[filename].sources.update(there.sources)
						
				else:
					conflicts.add(filename)
					
		return r, conflicts

json_encoder.register(Commit)

