
import os
import os.path
import json
import fnmatch
import hashlib
import uuid
import logging
import socket

import json_encoder
import protocol
from file_info import FileInfo
from commit import Commit

class Repository:
	
	def __init__(self, location):
		self.location = location
	
	def get_repository_id(self):
		self.load_config()
		return self.config['id']
	
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
	
	def harmony_dir(self, subpath = ''):
		return os.path.join(self.location, '.harmony', subpath)
	
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
		
	def load_remotes(self):
		self.remotes = self.load_json_config('remotes', {})
		
	def save_remotes(self):
		self.save_json_config('remotes', self.remotes)
		
	
	#
	# File rules
	# 
	
	def pattern_match(self, pattern, path):
		return fnmatch.fnmatch(path, pattern)
	
	def get_rules(self, p):
		relative_path = self.make_relative(p)
		
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
	 
	def set_head(self, hid):
		path = os.path.join(self.harmony_dir(), 'HEAD')
		open(path, 'w').write(hid.strip())
	
	def head_id(self):
		path = os.path.join(self.harmony_dir(), 'HEAD')
		if not os.path.exists(path):
			return None
		return open(path, 'r').read().strip()
		
	
	def head(self):
		return get_commit(self.head_id())
	
	def get_commit(self, commit_id):
		filepath = os.path.join(self.harmony_dir(), 'commits/' + commit_id)
		return json.load(open(filepath, 'r'), object_hook = json_encoder.object_hook)
	
	def add_commit(self, c):
		s = json.dumps(c,
				cls = json_encoder.JSONEncoder,
				separators = (',', ': '),
				indent = 2,
				sort_keys = True,
		)
		h = hashlib.sha256(s.encode('utf-8')).hexdigest()
		filepath = os.path.join(self.harmony_dir(), 'commits/' + h)
		open(filepath, 'w').write(s)
		return h
	
	#
	# Repository commands
	# 
	
	def make_config(self, nickname = None):
		self.load_config()
		# TODO: don't do this if a config already exists!
		myid = str(uuid.uuid1())
		self.config['id'] = myid
		if nickname is None:
			nickname = socket.gethostname()
		self.config['nickname'] = nickname
		self.save_config()
		
		self.load_remotes()
		if myid not in self.remotes:
			self.remotes[myid] = {}
		self.remotes[myid]['uri'] = '.'
		self.remotes[myid]['nickname'] = nickname
		self.save_remotes()
	
	def init(self, nickname = None):
		os.makedirs(self.harmony_dir('commits'))
		self.make_config()
		
	def clone(self, uri):
		os.makedirs(self.harmony_dir())
		
		proto = protocol.find_protocol(uri)
		proto.get_recursive(uri, '.harmony/commits', self.harmony_dir('commits'))
		proto.get_file(uri, '.harmony/HEAD', self.harmony_dir('HEAD'))
		proto.get_file(uri, '.harmony/remotes', self.harmony_dir('remotes'))
		
		self.make_config()
		
		# TODO: use proper tempfile here
		proto.get_file(uri, '.harmony/config', '/tmp/remote_config')
		remote_cfg = json.load(open('/tmp/remote_config', 'r'))
		remote_id = remote_cfg['id']
		remote_nickname = remote_cfg.get('nickname', 'origin')
		
		self.load_remotes()
		if remote_id not in self.remotes:
			self.remotes[remote_id] = {}
		self.remotes[remote_id]['nickname'] = remote_nickname
		self.remotes[remote_id]['uri'] = uri
		self.save_remotes()
		
	def commit(self):
		s = Commit(self)
		
		parent_id = self.head_id()
		if parent_id is not None:
			s.add_parent(parent_id)
		
		changed = False
		
		for root, dirs, files in os.walk(self.location):
			for filename in files:
				rules = self.get_rules(os.path.join(root, filename))
				fi = FileInfo(open(os.path.join(root, filename), 'rb'))
				fi.sources.add(self.get_repository_id())
				relfn = self.make_relative(os.path.join(root, filename))
				parent_fi = None
				if parent_id is not None:
					parent_fi = self.get_commit(parent_id).get_file(relfn)
					
				if 'ignore' in rules:
					logging.debug('ignoring {}'.format(relfn))
					if parent_fi is not None:
						if fi.content_id != parent_fi.content_id:
							logging.warn('ignored file {} diverged from repository'.format(relfn))
						s.add_file(relfn, parent_fi)
						
				else:
					if parent_fi is not None:
						# File (with that name) has been there before
						if fi.content_id != parent_fi.content_id:
							# File has changed 
							logging.info('updated {}'.format(relfn))
							s.add_file(relfn, fi)
							changed = True
							
						else:
							# File has not changed
							fi.sources.update(parent_fi.sources)
							s.add_file(relfn, fi)
							
					else:
						# File has not been here before
						logging.info('created {}'.format(relfn))
						s.add_file(relfn, fi)
						changed = True
	
		if changed:
			commit_id = self.add_commit(s)
			self.set_head(commit_id)
		else:
			logging.info('nothing to commit')
			
	def fetch(self, remote):
		r = self.get_remote(remote)
		r.fetch(self.remote_dir(remote.name))
	
	def whereis(self, relpath):
		self.load_remotes()
		
		cid = self.head_id()
		while cid is not None:
			c = self.get_commit(cid)
			f = c.get_file(relpath)
			if f is not None:
				for s in f.sources:
					if s in self.remotes:
						print("{} {:20s} {}".format(s, self.remotes[s].get('nickname', ''),
							self.remotes[s].get('uri', '')))
					else:
						print(s)
				return
			if len(c.parents) != 1: break
			cid = c.parents[0]
		logging.info('{} not found in history'.format(relpath))

