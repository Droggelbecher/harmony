
import protocol

class Remote:
	def __init__(self, name, uri):
		self.name = name
		self.uri = uri
		self.repository = repository
		
	def fetch(self, local_dir):
		protocol = protocol.find_protocol(self.uri)
		protocol.get_file(
				self.uri, '.harmony/history',
				os.path.join(local_dir, 'history')
		)

