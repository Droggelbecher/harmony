
import hashlib

class HashlibHasher:
	def __init__(self, name):
		self.prefix = name
		self.hasher = hashlib.new(name)
		
	def hash(self, f):
		self.hasher.update(f.read())
		return self.prefix + ':' + self.hasher.hexdigest()
		

