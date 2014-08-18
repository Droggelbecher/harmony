# vim: set ts=4 sw=4 noexpandtab:

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
from commit_difference import CommitDifference, Edit, Deletion, Rename, Creation
from conflict import Conflict

import configuration
import history

class Repository:
	
	def __init__(self, location):
		self.location = os.path.normpath(os.path.abspath(location))
		self.configuration = configuration.Configuration(self.relpath_hd())
		self.history = history.History(self)
		self.rules = rules.Rules(self)

	def id(self):
		return self.configuration.get('id')

	def name(self):
		return self.configuration.get('name')

	def head(self):
		return self.history.head()


	def commit(self):
		"""
		Commit the working dir state to the history, moving HEAD.
		"""
		#c = Commit(self)
		
		#parent_id = self.get_head_id()
		
		## Copy states from parent
		
		#if parent_id is not None:
			#c.add_parent(parent_id)
			#parent = self.get_commit(parent_id)
			#c.add_files_from(parent)
		
		c = self.history.create_commit(on_top = True)
		
		changed = False
		seen_files = set()
		
		# Add/update files from working dir
		# {{{
		
		for root, dirs, files in os.walk(self.location):
			for filename in files:
				absfn = os.path.join(root, filename)
				relfn = self.relpath_wd(absfn)
				seen_files.add(relfn)

				rule = self.rules.get(relfn)
				with open(relfn, 'rb') as f:
					new_fi = FileInfo(f)
				fi = None

				# See whether this file is already being tracked 
				#
				if relfn in c.get_filenames():
					prev_fi = c.get_file(relfn)
					fi = c.get_file(relfn)

				if fi:
					# File is tracked
					if self.get_repository_id() in fi.sources:
						if not rule.commit_tracked:
							logging.debug('ignoring tracked file {}'.format(relfn))
							continue
						
						# File is supposed to be in present in the working
						# directory
						if new_fi.content_id != fi.content_id:
							# File content has changed 
							changed = True
							logging.info('updated {}'.format(relfn))
							new_fi.action = 'updated'
							new_fi.sources.add(self.get_repository_id())
							c.add_file(relfn, new_fi)
							
						# else: file has not changed, nothing to do
					else:
						# File is tracked but not expected in this working
						# directory (nonlocal).
						if not rule.commit_nonlocal_tracked:
							logging.debug('ignoring nonlocal tracked file {}'.format(relfn))
							continue
						
						if new_fi.content_id != fi.content_id:
							# File content has changed 
							changed = True
							logging.info('updated nonlocal {}'.format(relfn))
							new_fi.action = 'updated'
							new_fi.sources.add(self.get_repository_id())
							c.add_file(relfn, new_fi)
							
				else:
					# File is untracked
					if not rule.commit_untracked:
						logging.debug('ignoring untracked file {}'.format(relfn))
						continue
					changed = True
					logging.info('created {}'.format(relfn))
					new_fi.action = 'created'
					new_fi.sources.add(self.get_repository_id())
					c.add_file(relfn, new_fi)
		# }}}
		
		# Handle deletions
		deletions = set(c.get_filenames()).difference(seen_files)
		
		for relfn in deletions:
			fi = None
			if relfn in c.get_filenames():
				prev_fi = c.get_file(relfn)
				fi = c.get_file(relfn)

			if fi and self.get_repository_id() in fi.sources:
				#
				# Build the new info block for this file,
				# copy from the old one, but we are not a source anymore.
				#
				new_fi = fi.copy()
				new_fi.sources.discard(self.get_repository_id())
				if not new_fi.sources:
					logging.info('exterminated "{}" (no sources left)'.format(relfn))
					c.delete_file(relfn)
				else:
					logging.info('deleted "{}" ({} sources left)'.format(relfn, len(new_fi.sources)))
					c.edit_file(relfn, new_fi)
				changed = True
		
		if changed:
			commit_id = self.add_commit(c)
			self.set_head(commit_id)
		else:
			logging.info('nothing to commit')
		

















	
	def get_repository_id(self):
		self.load_config()
		return self.config['id']
	
	def get_repository_nickname(self):
		self.load_config()
		return self.config['nickname']
	
	#
	# Utility functions
	# 
	
	def relpath_wd(self, path):
		"""
		Return version of path that is relative to the working directory
		(self.location)
		"""
		relpath = os.path.relpath(os.path.abspath(path),
				os.path.abspath(self.location))
		return relpath
	
	def relpath_hd(self, path = ''):
		"""
		Return version of path that is relative to the harmony directory
		(self.harmony_dir())
		"""
		relpath = os.path.relpath(os.path.abspath(path),
				os.path.abspath(self.harmony_dir()))
		return relpath
	
	#
	# Directories, loading/saving config files, etc...
	#
	
	def harmony_dir(self, subpath = ''):
		return os.path.join(self.location, '.harmony', subpath)
	
	def remote_dir(self, name):
		return os.path.join(self.harmony_dir, 'remotes', name)
	
	def temp_dir(self, subpath = ''):
		return os.path.join(self.harmony_dir('tmp'), subpath)
		
	def commit_dir(self, c=''):
		return self.harmony_dir(os.path.join('commits', c))
	
	
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
	
	def get_rules(self, p): return self.configuration.get_rules()
	
	#
	# History
	# 
	 
	#def set_head(self, hid):
		#assert isinstance(hid, str)
		#path = os.path.join(self.harmony_dir(), 'HEAD')
		#with open(path, 'w') as f:
			#f.write(hid.strip())
	
	#def get_head_id(self, subpath='HEAD'):
		#path = self.harmony_dir(subpath) #os.path.join(self.harmony_dir(), 'HEAD')
		#if not os.path.exists(path):
			#return None
		#with open(path, 'r') as f:
			#r = f.read().strip()
		#return r
	
	#def get_head(self, subpath='HEAD'):
		#return self.get_commit(self.get_head_id(subpath=subpath))
	
	#def has_commit(self, commit_id):
		#filepath = self.commit_dir(commit_id)
		#return os.path.exists(filepath)
	
	#def get_commit(self, commit_id):
		#filepath = self.commit_dir(commit_id)
		#with open(filepath, 'r') as f:
			#r = json.load(f, object_hook = json_encoder.object_hook)
		#return r
	
	#def add_commit(self, c):
		#s = json.dumps(c,
				#cls = json_encoder.JSONEncoder,
				#separators = (',', ': '),
				#indent = 2,
				#sort_keys = True,
		#)
		#h = hashlib.sha256(s.encode('utf-8')).hexdigest()
		#filepath = self.commit_dir(h)
		#with open(filepath, 'w') as f:
			#f.write(s)
		#self.set_head(h)
		#return h
	
	#
	# Remotes
	# 
	
	def get_remote(self, remote_id, allow_nickname = True):
		self.load_remotes()
		if remote_id not in self.remotes:
			if allow_nickname:
				for k, v in self.remotes.items():
					if v['nickname'] == remote_id:
						return Remote(self, k, v['uri'], v['nickname'])
					
			#for k, v in self.remotes.items():
				#if Remote.equivalent_uri(remote_id, v['uri']):
			return Remote(self, '0', remote_id, '_direct')
			
			return None
		d = self.remotes[remote_id]
		return Remote(self, remote_id, d['uri'], d['nickname'])
	
	#
	# Repository commands
	# 
	
	def cmd_init(self, nickname = None):
		return self.init(nickname)
	
	def cmd_clone(self, uri):
		return self.clone(uri)
	
	#def cmd_pull_state(self, remote_id = 'origin'):
		#conflicts, commit_id = self.pull_state(remote_id)
		#if conflicts:
			#for filename, conflict_type in conflicts:
				#print("CONFLICT: {} {}
	

	# TODO: do all configuration stuff via the configuration module	

	def make_config(self, nickname = None):
		self.load_config()
		# TODO: don't do this if a config already exists!
		myid = str(uuid.uuid1())
		self.config['id'] = myid
		if nickname is None:
			nickname = '{}-{}'.format(os.path.basename(self.location), socket.gethostname())
		self.config['nickname'] = nickname
		self.save_config()
		
		self.load_remotes()
		if myid not in self.remotes:
			self.remotes[myid] = {} #{ 'id': myid }
		self.remotes[myid]['uri'] = '.'
		self.remotes[myid]['nickname'] = nickname
		self.save_remotes()
	
	def init(self, nickname = None):
		os.makedirs(self.commit_dir())
		os.makedirs(self.temp_dir())
		self.make_config(nickname = nickname)
		
	def pull_state(self, remote_id):
		"""
		Synchronize state with all known & reachable remotes.
		Note that this does not transfer any payload (i.e. does not alter
		the working copy), but only updates the history.
		"""
		
		self.load_remotes()
		myhead = self.get_head_id()
		
		remote_info = self.get_remote(remote_id)
		if remote_info is None:
			raise Exception('remote {} not found'.format(remote_id))
		
		#for remote_id, remote_info in self.remotes.items():
		if remote_info.uri == 'file:.':
			raise Exception("refusing to pull myself")
		
		remote = self.get_remote(remote_id)
		proto = remote.get_protocol()
		
		tmpfilehandle, tmpfilename = tempfile.mkstemp(dir = self.temp_dir())
		reltmpfilename = self.relpath_hd(tmpfilename)
		os.close(tmpfilehandle)
		
		try:
			proto.get_file(remote.uri, '.harmony/HEAD', tmpfilename)
			remote_head_id = self.get_head_id(reltmpfilename)
			xs = set([remote_head_id])
			
			# Is the set of remote commits a subset of our commits?
			# If we contain their HEAD, it must be!
			remote_is_subset = self.has_commit(remote_head_id)
			
			if remote_is_subset:
				logging.info("Already up to date.")
				# Nothing to do for this remote, we are more up to date than them.
				return [], myhead
			
			# Now find out
			# wheter the set of our commits is a subset of the remote
			# commits, i.e. we contain their HEAD,
			# 
			# Also, get all remote commits below remote HEAD that are
			# not available locally
			#remote_is_superset = False
			lowest_common_ancestor = None
			while xs:
				x = xs.pop()
				if self.has_commit(x):
					#if x == myhead:
						#remote_is_superset = True
					#else:
					
					lowest_common_ancestor = x
					break
						
				else:
					proto.get_file(remote.uri, '.harmony/commits/' + x, self.commit_dir(x))
					xs.update(self.get_commit(x).get_parents())
			
			if lowest_common_ancestor == myhead:
				# We are a clean subset of the remote graph,
				# just fast forward
				logging.info("Fast-forward.")
				self.set_head(remote_head_id)
				return [], remote_head_id
				
			if lowest_common_ancestor is None:
				raise Exception("Branches are not related!")
				
			else:
				# Commits on both sides happened, merge!
				conflicts, commit_id = self.merge(
						base_id = lowest_common_ancestor,
						local_id = myhead,
						remote_id = remote_head_id)
				if conflicts:
					print("Automatic merge failed.")
					for conflict in conflicts:
						print(conflict)
					
				logging.info("Merge.")
				return conflicts, commit_id
			
		finally:
			os.unlink(tmpfilename)
	
	def merge(self, base_id, local_id, remote_id, conflict_resolutions = {}):
		base = self.get_commit(base_id)
		local = self.get_commit(local_id)
		remote = self.get_commit(remote_id)
		
		merge = Commit(self)
		merge.set_parents((local_id, remote_id))
		merge.add_files_from(local)
		merge.add_files_from(remote)
		
		conflicts = []
		#diff_local = self.difference(local, base)
		#diff_remote = self.difference(remote, base)
		
		diff_local = CommitDifference(base, local)
		diff_remote = CommitDifference(base, remote)
		
		#merge.files = base.files.copy()
		
		# local   remote   conflict condition
		# 
		# target conflicts:
		#  
		# edit a  edit a   C: contentL(a) != contentR(a)
		# mv a b  edit b   C: contentL(b) != contentR(b)
		# edit b  mv a b   C: contentL(b) != contentR(b)
		# mv a b  mv c b   C: contentL(b) != contentR(b)
		# rm a    edit a   C!
		# edit a  rm a     C!
		# 
		# name conflicts:
		# 
		# mv a b  mv a c   C: b != c
		# rm a    mv a b   C!
		# mv a b  rm a     C!
		# 
		# TODO: order conflicts:
		# 
		# mv a b  mv b c   remote before local
		# mv b c  mv a b   local before remote
		# 
		# non-conflicts:
		# 
		# mv a b  edit a   [b] = remote[a] (apply edit first)
		# edit a  mv a b   [b] = local[a]  (apply edit first)
		# 
		
		#
		# Target conflicts: Operations on both sides yielding different
		# content for the same filename
		# 
		
		targets_l = diff_local.get_changes_by_target()
		targets_r = diff_remote.get_changes_by_target()
		
		intersection = set(targets_l.keys()).intersection(targets_r.keys())
		
		for filename in intersection:
			local_content_id = None
			local_fi = local.get_file(filename)
			if local_fi: local_content_id = local_fi.content_id
			
			remote_content_id = None
			remote_fi = remote.get_file(filename)
			if remote_fi: remote_content_id = remote_fi.content_id
			
			if local_content_id != remote_content_id:
				# There actually is a clash, determine details
				conflicts.append(Conflict('target', filename, 
					targets_l.get(filename, None), targets_r.get(filename, None)))
				
		#
		# Name conflicts: Operations on both sides renaming a file differently
		#
		
		sources_l = diff_local.get_changes_by_source()
		sources_r = diff_remote.get_changes_by_source()
		
		for filename in set(sources_l.keys()).union(sources_r.keys()):
			l = sources_l.get(filename, None)
			r = sources_r.get(filename, None)
			if l != r:
				conflicts.append(Conflict('source', filename, l, r))
				
		if not conflicts:
			# Apply changes
			
			def cmp_changes(c1, c2):
				# Ensure edits happen before renames, this way if both happen
				# to the same file, they can be both applied easily
				if isinstance(c1, Edit) and isinstance(c2, Rename):
					return -1
				elif isinstance(c1, Rename) and isinstance(c2, Edit):
					return 1
				return cmp(c1, c2)
			
			def key_changes(c):
				# Ensure edits happen before renames, this way if both happen
				# to the same file, they can be both applied easily
				if isinstance(c, Edit): return (0, c)
				elif isinstance(c, Rename): return (1, c)
				return (2, c)
				
			
			diff_both = sorted(diff_local + diff_remote, key=key_changes)
			for change in diff_both:
				merge.apply_change(change)
			
			self.add_commit(merge)
		
		return conflicts, None
	
	def clone(self, uri):
		os.makedirs(self.harmony_dir())
		os.makedirs(self.temp_dir())
		#os.makedirs(self.commit_dir())
		
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
			self.remotes[remote_id] = {} # 'id': remote_id }
		self.remotes[remote_id]['nickname'] = remote_nickname
		self.remotes[remote_id]['uri'] = uri
		self.save_remotes()
		
	def commit(self):
	def get_sources(self, relpath):
		cid = self.get_head_id()
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
		# TODO: should we get the newest version of the file (and make a new
		# commit)
		# or the one that matches our HEAD?
		# -> at the very least we should warn if we find newer versions are
		# out there than the one we are requesting
		# -> not implicitely committing sounds more deterministic

		for src in self.get_sources(relpath):
			remote = self.get_remote(src)
			if src is None:
				logging.warning('no info available about remote {}, ignoring'.format(s))
				continue
			remote.get(relpath)
			
			# this sucks.
			# Remote-commiting doesnt sound like a good idea,
			# not communicating the state is counterintuitive as well.
			# What is the way to go here?
			
			# TODO: Let remote repository know, we got a copy of this file
			if remote.is_writeable():
				# TODO: add new commit with updated source
				XXX
			else:
				logging.warning('remote {} is not writable, the other end will not realize we have a copy until it pulls from us!',
remote)
				
				
			return
		logging.error('no remote found to provide {}'.format(relpath))
	
	def available_files(self):
		"""
		Return all files that were known/assumed
		to exist in the last commit (HEAD)
		"""
		head = self.get_head()
		return head.get_filenames()
	
	def cmd_log(self):
		h = self.get_history()
		for cid, commit in h:
			print('commit {:8s} parents {:8s} {:8s}'.format(
				cid[-8:],
				commit.get_parents()[0][-8:] if len(commit.get_parents()) >= 1 else '',
				commit.get_parents()[1][-8:] if len(commit.get_parents()) >= 2 else ''
			))
			
			print('created {:%Y-%m-%d %H:%M} in {}'.format(commit.created,
				commit.repository_id))
			
			#for p in commit.parents:
				#print("  p {}".format(p[-8:]))
				
			if len(commit.get_parents()) == 0:
				for filename in commit.get_filenames():
					print('  A {}'.format(filename))
			elif len(commit.get_parents()) == 1:
				# TODO: this unecessarily reads the parent commit from disk
				# (do we care?).
				d = CommitDifference(self.get_commit(commit.get_parents()[0]), commit)
				for change in d.get_changes():
					print('  {}'.format(change.brief()))
			elif len(commit.get_parents()) == 2:
				print('  (merge)')
			print()
			
	def get_history(self):
		history = []
		c = self.get_head_id()
		branches = set([(c, self.get_commit(c))])
		
		while branches:
			# find next (in terms of date/time) commit
			max_commit = None
			max_commit_id = None
			for cid, b in branches:
				if max_commit is None or b.created > max_commit.created:
					max_commit = b
					max_commit_id = cid
			branches.discard((max_commit_id, max_commit))
			history.append((max_commit_id, max_commit))
			
			for cid in max_commit.get_parents():
				branches.add((cid, self.get_commit(cid)))
		return history
	
	
