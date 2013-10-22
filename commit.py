
from file_info import FileInfo
import json_encoder

class Commit:
	"""
	timestamp
	parents = []
	
	files = {
		'relative/path/to/file': FileInfo({
			'content-id': 'SHA256:1234567890123456',
			'meta-info': {
				'type': 'MP3',
				'artist': 'Led Zeppelin',
			},
			'sources': set(['calculon', 'r2d2']),
		})
	}
	"""
	
	def __init__(self):
		self.parents = set()
		self.files = {}
		
	def serialize(self):
		return {
			'parents': self.parents,
			'files': self.files,
		}
	
	def add_file(self, relative_path, fi):
		self.files[relative_path] = fi
	
	def lca(self, other):
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

