
import os
import os.path
import json
import fnmatch
import hashlib
import uuid
import logging
import socket
import tempfile

import json_encoder
import protocol
import protocols.file
from file_info import FileInfo
from commit import Commit
from remote import Remote

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
			with open(filepath, 'w') as f:
				json.dump(default, f)
			
		try:
			with open(filepath, 'r') as f:
				obj = json.load(f)
		except ValueError:
			obj = {}
		return obj
	
	def save_json_config(self, name, data):
		filepath = os.path.join(self.harmony_dir(), name)
		with open(filepath, 'w') as f:
			json.dump(data, f, sort_keys=True, indent=2,
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
		with open(path, 'w') as f:
			f.write(hid.strip())
	
	def head_id(self):
		path = os.path.join(self.harmony_dir(), 'HEAD')
		if not os.path.exists(path):
			return None
		with open(path, 'r') as f:
			r = f.read().strip()
		return r
		
	
	def head(self):
		return get_commit(self.head_id())
	
	def get_commit(self, commit_id):
		filepath = os.path.join(self.harmony_dir(), 'commits/' + commit_id)
		with open(filepath, 'r') as f:
			r = json.load(f, object_hook = json_encoder.object_hook)
		return r
	
	def add_commit(self, c):
		s = json.dumps(c,
				cls = json_encoder.JSONEncoder,
				separators = (',', ': '),
				indent = 2,
				sort_keys = True,
		)
		h = hashlib.sha256(s.encode('utf-8')).hexdigest()
		filepath = os.path.join(self.harmony_dir(), 'commits/' + h)
		with open(filepath, 'w') as f:
			f.write(s)
		return h
	
	#
	# Remotes
	# 
	
	def get_remote(self, remote_id):
		self.load_remotes()
		if remote_id not in self.remotes:
			return None
		d = self.remotes[remote_id]
		return Remote(self, remote_id, d['uri'], d['nickname'])
	
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
		try:
			proto.get_file(uri, '.harmony/HEAD', self.harmony_dir('HEAD'))
		except FileNotFoundError:
			logging.warning('remote repo does not have a HEAD (probably you havent committed there yet?)')
		proto.get_file(uri, '.harmony/remotes', self.harmony_dir('remotes'))
		
		self.make_config()
		
		fd, tmpfilename = tempfile.mkstemp()
		os.close(fd)
		try:
			proto.get_file(uri, '.harmony/config', tmpfilename)
			with open(tmpfilename, 'r') as f:
				remote_cfg = json.load(f)
		finally:
			os.remove(tmpfilename)
		
		remote_id = remote_cfg['id']
		remote_nickname = remote_cfg.get('nickname', 'origin')
		
		self.load_remotes()
		if remote_id not in self.remotes:
			self.remotes[remote_id] = {}
		self.remotes[remote_id]['nickname'] = remote_nickname
		self.remotes[remote_id]['uri'] = uri
		self.save_remotes()
		
	def commit(self):
		c = Commit(self)
		
		parent_id = self.head_id()
		
		# Copy states from parent
		
		if parent_id is not None:
			c.add_parent(parent_id)
			parent = self.get_commit(parent_id)
			c.files = parent.files.copy()
		
		# Add/update files from working dir
		
		changed = False
		for root, dirs, files in os.walk(self.location):
			for filename in files:
				absfn = os.path.join(root, filename)
				relfn = self.make_relative(absfn)
				rules = self.get_rules(relfn)
				with open(relfn, 'rb') as f:
					new_fi = FileInfo(f)
				fi = None
				if relfn in c.files:
					prev_fi = c.files[relfn]
				
				if 'ignore' in rules:
					logging.debug('ignoring {}'.format(relfn))
					if fi and new_fi.content_id != fi.content_id:
						logging.warn('local version of ignored file {} differs from repo version'.format(relfn))
						
				else:
					if fi and new_fi.content_id != fi.content_id:
						changed = True
						logging.info('updated {}'.format(relfn))
						new_fi.action = 'updated'
						new_fi.sources.add(self.get_repository_id())
						c.files[relfn] = new_fi
					
					elif not fi:
						changed = True
						logging.info('created {}'.format(relfn))
						new_fi.action = 'created'
						new_fi.sources.add(self.get_repository_id())
						c.files[relfn] = new_fi
		if changed:
			commit_id = self.add_commit(c)
			self.set_head(commit_id)
		else:
			logging.info('nothing to commit')
		
	def get_sources(self, relpath):
		cid = self.head_id()
		if cid is not None:
			c = self.get_commit(cid)
			f = c.get_file(relpath)
			if f is not None:
				return f.sources
		return []
	
	def whereis(self, relpath):
		self.load_remotes()
		for s in self.get_sources(relpath):
			if s in self.remotes:
				print("{} {:20s} {}".format(s, self.remotes[s].get('nickname', ''),
					self.remotes[s].get('uri', '')))
			else:
				logging.warning('no info available about remote {}'.format(s))
				print(s)
		else:
			logging.info('{} not found in repository'.format(relpath))
			
	def get(self, relpath):
		for src in self.get_sources(relpath):
			remote = self.get_remote(src)
			if src is None:
				logging.warning('no info available about remote {}, ignoring'.format(s))
				continue
			remote.get(relpath)
			return
		logging.error('no remote found to provide {}'.format(relpath))

