
import hashers
from hashers.hashlib_hasher import HashlibHasher
import copy
import json_encoder

class FileInfo:
		
	def __init__(self, f = None, hash_=HashlibHasher('sha256').hash):
		if f is not None:
			self.content_id = hash_(f)
		else:
			self.content_id = None
		self.sources = set()
		self.action = None
		
	def serialize(self):
		return {
			'content_id': self.content_id,
			'sources': list(self.sources),
			'action': self.action,
		}
		
	@staticmethod
	def deserialize(dct):
		r = FileInfo()
		r.content_id = dct['content_id']
		r.sources = dct['sources']
		r.action = dct.get('action', None)
		return r
		
	def copy(self):
		return copy.copy(self)

	def __eq__(self, other):
		return self.content_id == other.content_id

json_encoder.register(FileInfo)

