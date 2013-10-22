
import hashers
from hashers.hashlib_hasher import HashlibHasher
import copy
import json_encoder

class FileInfo:
		
	def __init__(self, f, hash_=HashlibHasher('sha256').hash):
		self.content_id = hash_(f)
		self.sources = set()
		
	def serialize(self):
		return {
			'content_id': self.content_id,
			'sources': list(self.sources)
		}
		
	def copy(self):
		return copy.copy(self)

	def __eq__(self, other):
		return self.content_id == other.content_id

json_encoder.register(FileInfo)

