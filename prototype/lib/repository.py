# vim: set ts=4 sw=4 noexpandtab:
#
import sys
sys.path.append('lib')

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
		self.configuration = configuration.Configuration(self, self.harmony_dir())
		self.history = history.History(self)

	def id(self):
		return self.configuration.get_config('id')

	def name(self):
		return self.configuration.get_config('name')

	def nickname(self):
		return self.configuration.get_config('nickname')

	def head(self):
		return self.history.head()


	def commit(self):
		c = self.history.create_commit(on_top = True)
		seen_files = set()
		changed = False

		for root, dirs, files in os.walk(self.location):
			for filename in files:
				absfn = os.path.join(root, filename)
				relfn = self.relpath_wd(absfn)
				rule = self.configuration.get_rule(relfn)
				seen_files.add(relfn)

				# new_fi is the file info of the file as it is present in the
				# working directory
				with open(relfn, 'rb') as f:
					new_fi = FileInfo(f)

				# fi is the file info of the previously commited state,
				# if available (else None)
				parent_ids = c.get_parents().copy()
				assert len(parent_ids) in (0, 1)
				fi = None
				if len(parent_ids):
					parent = self.history.get_commit(parent_ids.pop())
					if relfn in parent.get_filenames():
						fi = parent.get_file(relfn)
					else:
						logging.debug("--- {} not known to parent".format(relfn))
				else:
					logging.debug("--- no parents")

				if fi:
					# File with that name has been tracked before
					# by this repository
					if not rule.commit_tracked:
						logging.debug('ignoring tracked file {}'.format(relfn))
						continue

					new_fi.sources = fi.sources.union(set([self.id()]))

					# Either content or sources changed
					if new_fi.content_id != fi.content_id or new_fi.sources != fi.sources:
						if new_fi.content_id != fi.content_id:
							logging.info('updated content: {}'.format(relfn))
						if new_fi.sources != fi.sources:
							logging.info('updated sources: {}'.format(relfn))
						new_fi.action = 'updated'
						c.add_file(relfn, new_fi)
						changed = True

				elif not fi:
					# Haven't seen that file before at all,
					if not rule.commit_untracked:
						logging.debug('ignoring untracked file {}'.format(relfn))
						continue

					new_fi.sources.add(self.id())
					logging.info('created {}'.format(relfn))
					new_fi.action = 'created'
					c.add_file(relfn, new_fi)
					changed = True

		# Handle file deletions.
		# A file is considered deleted if it has been marked in the history as
		# present in this repository instance but can not be found in the
		# filesystem anymore.
		unseen_files = set(c.get_filenames()).difference(seen_files)
		for fn in unseen_files:
			fi = c.get_file(fn)
			if self.id() in fi.sources:
				new_fi = fi.copy()
				new_fi.sources.discard(self.id())
				if not new_fi.sources:
					logging.info('exterminated "{}" (no sources left)'.format(relfn))
					c.delete_file(relfn)
				else:
					logging.info('deleted "{}" ({} sources left)'.format(relfn, len(new_fi.sources)))
					c.edit_file(relfn, new_fi)
				changed = True

		if changed:
			commit_id = self.history.save_commit(c)
			self.history.set_head_id(commit_id)
		else:
			logging.info('nothing to commit')

	def commit_(self):
		"""
		Commit the working dir state to the history, moving HEAD.
		"""
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

				rule = self.configuration.get_rule(relfn)
				with open(relfn, 'rb') as f:
					new_fi = FileInfo(f)
				fi = None

				# See whether this file is already being tracked 
				#
				if relfn in c.get_filenames():
					prev_fi = c.get_file(relfn)
					fi = c.get_file(relfn)

				if fi:
					# File is tracked by this repo
					if self.id() in fi.sources:
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
							new_fi.sources.add(self.id())
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
							new_fi.sources.add(self.id())
							c.add_file(relfn, new_fi)
							
				else:
					# File is untracked
					if not rule.commit_untracked:
						logging.debug('ignoring untracked file {}'.format(relfn))
						continue
					changed = True
					logging.info('created {}'.format(relfn))
					new_fi.action = 'created'
					new_fi.sources.add(self.id())
					c.add_file(relfn, new_fi)
		# }}}
		
		# Handle deletions
		deletions = set(c.get_filenames()).difference(seen_files)
		
		for relfn in deletions:
			fi = None
			if relfn in c.get_filenames():
				prev_fi = c.get_file(relfn)
				fi = c.get_file(relfn)

			if fi and self.id() in fi.sources:
				#
				# Build the new info block for this file,
				# copy from the old one, but we are not a source anymore.
				#
				new_fi = fi.copy()
				new_fi.sources.discard(self.id())
				if not new_fi.sources:
					logging.info('exterminated "{}" (no sources left)'.format(relfn))
					c.delete_file(relfn)
				else:
					logging.info('deleted "{}" ({} sources left)'.format(relfn, len(new_fi.sources)))
					c.edit_file(relfn, new_fi)
				changed = True
		
		if changed:
			commit_id = self.history.save_commit(c)
			self.history.set_head_id(commit_id)
		else:
			logging.info('nothing to commit')
		
	#
	# Directory/Path Utility functions
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
	
	def harmony_dir(self, subpath = ''):
		return os.path.join(self.location, '.harmony', subpath)
	
	def remote_dir(self, name):
		return os.path.join(self.harmony_dir, 'remotes', name)
	
	def temp_dir(self, subpath = ''):
		return os.path.join(self.harmony_dir('tmp'), subpath)
		
	def commit_dir(self, c=''):
		return self.harmony_dir(os.path.join('commits', c))
	
	#
	# Remotes
	# 
	
	def get_remote(self, remote_id, allow_nickname = True):
		"""
		Return the remote with the given id
		"""
		#self.load_remotes()
		remotes = self.configuration.get_remotes()
		if remote_id not in remotes:
			if allow_nickname:
				for k, v in remotes.items():
					if v['nickname'] == remote_id:
						return Remote(
								repository = self,
								remote_id = k,
								uri = v['uri'],
								nickname = v['nickname']
								)
					
			return None
		d = remotes[remote_id]
		return Remote(self, remote_id, d['uri'], d['nickname'])
	
	#
	# Repository commands
	# 
	
	def init(self, nickname = None):
		"""
		Initialize the working directory
		"""
		os.makedirs(self.commit_dir())
		os.makedirs(self.temp_dir())
		self.configuration.create_files(nickname = nickname)

	def pull_state(self, remote_id):
		"""
		Synchronize state with given remote.
		Note that this does not transfer any payload (i.e. does not alter
		the working copy), but only updates the history.
		"""
		
		myhead = self.history.get_head_id()
		
		remote_info = self.get_remote(remote_id)
		if remote_info is None:
			raise Exception('remote {} not found'.format(remote_id))
		
		if remote_info.uri == 'file:.':
			raise Exception("refusing to pull myself")
		
		remote = self.get_remote(remote_id)
		proto = remote.get_protocol()
		
		tmpfilehandle, tmpfilename = tempfile.mkstemp(dir = self.temp_dir())
		reltmpfilename = self.relpath_hd(tmpfilename)
		os.close(tmpfilehandle)
		
		try:
			proto.receive_file(remote.uri, '.harmony/HEAD', tmpfilename)
			remote_head_id = self.history.get_head_id(reltmpfilename)
			xs = set([remote_head_id])
			
			# Is the set of remote commits a subset of our commits?
			# If we contain their HEAD, it must be!
			remote_is_subset = self.history.has_commit(remote_head_id)
			
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
				if self.history.has_commit(x):
					lowest_common_ancestor = x
					break
						
				else:
					# TODO: Assymmetry: for pushing we just copy all commit
					# files, here we pull every commit we want on its own.
					# Also, pushing is implemented in remote.py while pulling
					# is implemented here.

					proto.receive_file(remote.uri, '.harmony/commits/' + x, self.commit_dir(x))
					xs.update(self.history.get_commit(x).get_parents())
			
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
					# TODO: Remove print statements
					logging.info("Automatic merge failed.")
					for conflict in conflicts:
						logging.info(conflict)
					
				logging.info("Merge.")
				return conflicts, commit_id
			
		finally:
			os.unlink(tmpfilename)
	
	def merge(self, base_id, local_id, remote_id, conflict_resolutions = {}):
		"""
		Merge two paths in the commit history.

		@param base_id common ancestor of the two merge paths
		@param local_id commit at the tip of the path considered 'local'
		@param remote_id commit at the tip of the path considered 'remote'
		@param conflict_resolutions TODO a dict that describes how to resolve
		conflicts TODO.

		@return pair (conflicts, commit_id). conflicts is a list of conflict
		objects describing what conflicts need to be resolved, if any. If there
		are no unresolved conflicts, a commit is actually created whose ID is
		returned in commit_id. Otherwise, commit_id is None.

		"""
		assert not conflict_resolutions, "Conflict resolution not implemented yet"

		logging.debug('merge(\n\tbase={}\n\tlocal={}\n\tremote={}\n)'.format(
			base_id, local_id, remote_id))

		base = self.history.get_commit(base_id)
		local = self.history.get_commit(local_id)
		remote = self.history.get_commit(remote_id)
		
		merge = Commit(self)
		merge.set_parents((local_id, remote_id))
		merge.add_files_from(local)
		merge.add_files_from(remote)
		
		conflicts = []
		diff_local = CommitDifference(base, local)
		diff_remote = CommitDifference(base, remote)
		
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
			
			cid = self.history.save_commit(merge)
			logging.debug('merge() created commit {}.'.format(cid))

		logging.debug('merge() finished with {} conflicts remaining.'.format(len(conflicts)))
		
		return conflicts, None
	
	def clone(self, uri):
		"""
		Clone the repository state (history) to the local working directory.

		@doctodo Specify how this should behave when there are already config
		files/history existing in the local harmony dir.
		"""

		os.makedirs(self.harmony_dir())
		os.makedirs(self.temp_dir())
		
		proto = protocol.find_protocol(uri)
		proto.receive_recursive(uri, '.harmony/commits', self.harmony_dir('commits'))
		try:
			proto.receive_file(uri, '.harmony/HEAD', self.harmony_dir('HEAD'))
		except FileNotFoundError:
			logging.warning('remote repo does not have a HEAD (probably you havent committed there yet?)')
		proto.receive_file(uri, '.harmony/remotes', self.harmony_dir('remotes'))
		
		self.configuration.create_files()
		
		fd, tmpfilename = tempfile.mkstemp()
		os.close(fd)
		try:
			proto.receive_file(uri, '.harmony/config', tmpfilename)
			with open(tmpfilename, 'r') as f:
				remote_cfg = json.load(f)
		finally:
			os.remove(tmpfilename)

		remotes = self.configuration.get_remotes()
		
		remote_id = remote_cfg['id']
		remote_nickname = remote_cfg.get('nickname', 'origin')
		
		if remote_id not in remotes:
			remotes[remote_id] = {} # 'id': remote_id }
		remotes[remote_id]['nickname'] = remote_nickname
		remotes[remote_id]['uri'] = uri

		self.configuration.set_remotes(remotes)
		
	def get_sources(self, relpath):
		"""
		Return a list of all remotes that are currently believed to contain a
		copy of the file specified by relpath.
		"""
		cid = self.history.get_head_id()
		if cid is not None:
			c = self.history.get_commit(cid)
			f = c.get_file(relpath)
			if f is not None:
				return f.sources
		return []
	
	def whereis(self, relpath):
		"""
		Pretty-print (to stdout) the result of get_sources for relpath.
		TODO: This shouldnt be here but rather is part of the CLI frontend.
		"""
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
		"""
		"""
		# TODO: should we get the newest version of the file (and make a new
		# commit)
		# or the one that matches our HEAD?
		# -> at the very least we should warn if we find newer versions are
		# out there than the one we are requesting
		# -> not implicitely committing sounds more deterministic

		for src in self.get_sources(relpath):
			assert src is not None
				
			logging.debug('checking whether {} is available from {}'.format(relpath, src))
			remote = self.get_remote(src)

			if remote is None:
				logging.warning('no info available about remote {}, ignoring'.format(src))
				continue

			remote.pull_file(relpath)
			
			# this sucks.
			# Remote-commiting doesnt sound like a good idea,
			# not communicating the state is counterintuitive as well.
			# What is the way to go here?

			# TODO: assert we are merged (only have one head!)
			new_head = self.commit()
			
			#if remote.is_writeable():
			if False:
				remote.push_history()
				remote.add_remote_head(new_head)
			else:
				logging.warning('remote {} is not writable, the other end will not realize we have a copy until it pulls from us!'.format(str(remote)))
				
				
			return
		logging.error('no remote found to provide {}'.format(relpath))
	
	def available_files(self):
		"""
		Return all files that were known/assumed
		to exist in the latest commit (HEAD)
		"""
		head = self.history.get_head()
		if head:
			return head.get_filenames()
		else:
			return []
	
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
					f = commit.get_file(filename)
					print('  I {} {}:...{:8s}'.format(
						filename, f.content_id.split(':')[0],
						f.content_id.split(':')[1][-8:]))
			elif len(commit.get_parents()) == 1:
				# TODO: this unecessarily reads the parent commit from disk
				# (do we care?).
				d = CommitDifference(self.history.get_commit(commit.get_parents()[0]), commit)
				for change in d.get_changes():
					print('  {}'.format(change.brief()))
			elif len(commit.get_parents()) == 2:
				print('  (merge)')
			print()
			
	def get_history(self):
		history = []
		cid = self.history.get_head_id()
		c = self.history.get_commit(cid)
		assert c is not None, "no HEAD"
		branches = set([(cid, c)])
		
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
				branches.add((cid, self.history.get_commit(cid)))
		return history
	
	
