
from file_info import FileInfo
import json_encoder

class Commit:
	def __init__(self, repo = None):
		self.parents = set()
		self.files = {}
		if repo:
			self.repository_id = repo.get_repository_id()
		else:
			self.repository_id = None
		
	def add_parent(self, parent):
		self.parents.add(parent)
	
	def empty(self):
		return len(self.files) == 0
	
	#
	# Serialization, Comparison
	# 
	
	def serialize(self):
		return {
			'creating_repository': self.repository_id,
			'parents': self.parents,
			'files': self.files,
		}
	
	@staticmethod
	def deserialize(dct):
		r = Commit()
		r.repository_id = dct['creating_repository']
		r.parents = dct['parents']
		r.files = dct['files']
		return r
		
	def add_file(self, relative_path, fi):
		self.files[relative_path] = fi
		
	def get_file(self, relative_path):
		return self.files.get(relative_path, None)
	
	def lca(self, other):
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
	
	def is_ancestor(self, other):
		return self.lca(other) == self
	
	def merge(self, other, conflict_resolutions = {}):
		
		# Is this a fast-forward?
		if self.is_ancestor(other): return other.copy(), set()
		if other.is_ancestor(self): return self.copy(), set()
		
		# Non-trivial merge
		r = RepositoryState()
		r.parents = (self, other)
		conflicts = set()
		
		filenames = set(self.files.keys()).union(set(other.files.keys()))
		
		for filename in filenames:
			if filename not in self.files:
				r.files[filename] = other.files[filename].copy()
				
			elif filename not in other.files:
				r.files[filename] = self.files[filename].copy()
				
			else:
				here = self.files[filename]
				there = other.files[filename]
				if here.content_id == there.content_id:
					r.files[filename] = here.copy()
					r.files[filename].sources.update(there.sources)
						
				else:
					conflicts.add(filename)
					
		return r, conflicts

json_encoder.register(Commit)

