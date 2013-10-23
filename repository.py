
import os
import os.path
import json
import fnmatch
import hashlib
from file_info import FileInfo
from commit import Commit
import uuid
import json_encoder

class Repository:
	
	def __init__(self, location):
		self.location = location
		
	#
	# Utility functions
	# 
	
	def make_relative(self, filename):
		relpath = os.path.relpath(os.path.abspath(filename),
				os.path.abspath(self.location))
		return relpath
	
	#
	# Directories, loading/saving config files, etc...
	#
	
	def harmony_dir(self):
		return os.path.join(self.location, '.harmony')
	
	def remote_dir(self, name):
		return os.path.join(self.harmony_dir, 'remotes', name)
	
	def load_json_config(self, name, default = {}):
		filepath = os.path.join(self.harmony_dir(), name)
		if not os.path.exists(filepath):
			json.dump(default, open(filepath, 'w'))
			
		try:
			obj = json.load(open(filepath, 'r'))
		except ValueError:
			obj = {}
		return obj
	
	def save_json_config(self, name, data):
		filepath = os.path.join(self.harmony_dir(), name)
		json.dump(data, open(filepath, 'w'), sort_keys=True, indent=2,
				separators=(',', ': '))
	
	def load_config(self):
		self.config = self.load_json_config('config', {})
		
	def save_config(self):
		self.save_json_config('config', self.config)
		
	def load_rules(self):
		self.rules = self.load_json_config('rules')
		if 'rules' not in self.rules:
			self.rules['rules'] = []
			self.save_rules()
		
	def save_rules(self):
		self.save_json_config('rules', self.rules)
		
	
	#
	# File rules
	# 
	
	def pattern_match(self, pattern, path):
		return fnmatch.fnmatch(path, pattern)
	
	def get_rules(self, p):
		relative_path = self.make_relative(p)
		print("get_rules({})".format(relative_path))
		
		self.load_rules()
		for r in self.rules['rules']:
			if self.pattern_match(r['pattern'], relative_path):
				return r['rules']
		
		# implicit rules:
		# ignore .harmony/
		if self.pattern_match('.harmony/*', relative_path):
			return ['ignore']
		
		return []
	
	#
	# History
	# 
	
	def head_id(self):
		path = os.path.join(self.harmony_dir(), 'HEAD')
		if not os.path.exists(path):
			return None
		return open(path, 'r').read().strip()
		
	
	def head(self):
		return get_commit(self.head_id())
	
	def get_commit(self, commit_id):
		self.load_json_config(self, os.path.join('commits', commit_id))
	
	def add_commit(self, c):
		s = json.dumps(c, cls = json_encoder.JSONEncoder)
		h = hashlib.sha256(s.encode('utf-8')).hexdigest()
		filepath = os.path.join(self.harmony_dir(), 'commits/' + h)
		open(filepath, 'w').write(s)
	
	#
	# Repository commands
	# 
	
	def init(self):
		os.makedirs(os.path.join(self.harmony_dir(), 'commits'))
		self.load_config()
		# TODO: don't do this if a config already exists!
		self.config['id'] = str(uuid.uuid1())
		self.save_config()
		
	def commit(self):
		s = Commit()
		
		hid = self.head_id()
		if hid is not None:
			s.add_parent(hid)
		
		for root, dirs, files in os.walk(self.location):
			for filename in files:
				rules = self.get_rules(os.path.join(root, filename))
				if 'ignore' not in rules:
					fi = FileInfo(open(os.path.join(root, filename), 'rb'))
					s.add_file(self.make_relative(filename), fi)
	
		if len(s.parents) != 1 or s != get_commit(s.parents[0]):
		#if s.is_nontrivial():
		# TODO: only add, if not exactly the same state as parent
			self.add_commit(s)
			
	def fetch(self, remote):
		r = self.get_remote(remote)
		r.fetch(self.remote_dir(remote.name))
		

