
import os
import logging

import protocol

class Remote:
	def __init__(self, repository, remote_id, uri, nickname):
		self.remote_id = remote_id
		self.nickname = nickname
		self.uri = uri
		self.repository = repository
	
	def get_protocol(self):
		return protocol.find_protocol(self.uri)
	
	def get(self, relpath):
		p = self.get_protocol()
		p.get_file(self.uri, relpath,
				os.path.join(self.repository.location, relpath))
	
