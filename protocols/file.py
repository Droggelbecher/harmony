
import shutil
import os
import os.path

class FileProtocol:
	name = 'file'
	
	def __init__(self):
		pass
	
	def to_dir(self, uri, remote_relative_path):
		return os.path.join(uri.split(':')[1], remote_relative_path)
	
	def get_file(self, uri, remote_relative_path, local_absolute_path):
		shutil.copyfile(to_dir(uri, remote_relative_dir), local_absolute_path)
	

