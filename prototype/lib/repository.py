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

from commit import Commit
from commit_difference import CommitDifference, Edit, Deletion, Rename, Creation
from conflict import Conflict
from file_info import FileInfo
from hashers.hashlib_hasher import HashlibHasher
from remote import Remote
import configuration
import hashers
import history
import json_encoder
import protocol
import protocols.file

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
		return self.history.get_head()

	def commit(self):
		c = self.history.create_commit(on_top = True, copy = True)

		# c is a full copy of the latest commit.
		# We want to update the info of this local instance, so weed that out
		# completely first.
		c.erase_source(self.id())

		# Get parent (if any)
		parents = c.get_parents().copy()
		assert len(parents) in (0, 1)
		if len(parents):
			p = set(parents.values()).pop()
		else:
			p = None

		for root, dirs, files in os.walk(self.location):
			for filename in files:
				absfn = os.path.join(root, filename)
				relfn = self.relpath_wd(absfn)
				rule = self.configuration.get_rule(relfn)

				if not rule.commit_tracked and \
						p is not None and p.has_file(relfn):
					logging.debug('ignoring tracked file {}'.format(relfn))
					continue

				if not rule.commit_untracked and \
						(p is None or not p.has_file(relfn)):
					logging.debug('ignoring untracked file {}'.format(relfn))
					continue

				cid = self.compute_content_id(absfn)
				c.add_source(relfn, cid, self.id())

				# Is this file (with the same contents) present in the parent
				# commit?
				same_in_parent = p is not None and (self.id() in p.get_repos_providing(relfn, cid))
				if not same_in_parent:
					c.set_default_version(relfn, cid)

		if p is None or c != p:
			commit_id = self.history.save_commit(c)
			self.history.set_head_id(commit_id)
		else:
			logging.info('nothing to commit')

		#seen_files = set()
		#changed = False

		#for root, dirs, files in os.walk(self.location):
			#for filename in files:
				#absfn = os.path.join(root, filename)
				#relfn = self.relpath_wd(absfn)
				#rule = self.configuration.get_rule(relfn)
				#seen_files.add(relfn)

				## new_fi is the file info of the file as it is present in the
				## working directory
				#with open(relfn, 'rb') as f:
					#new_fi = FileInfo(file = f)
				#new_fi.add_source(self)

				## fi is the file info of the previously commited state,
				## if available (else None)
				#parent_ids = c.get_parents().copy()
				#assert len(parent_ids) in (0, 1)

				#fi = None
				#if len(parent_ids):
					#parent = self.history.get_commit(parent_ids.pop())
					#fi = parent.get_file(relfn, self.id())

				## fi is either None or a FileInfo object for the previous
				## state of the file with the same name in this repository

				#if fi:
					## File with that name has been tracked before
					## by this repository
					#if not rule.commit_tracked:
						#logging.debug('ignoring tracked file {}'.format(relfn))
						#continue

					#if new_fi.content_id == fi.content_id:
						## Content of file has not changed
						## ...so availability has neither
						#new_fi.add_sources_from(fi)

					#else:
						## Content changed
						## Find all repositories that have the same content for
						## this filename
						#sources = parent.get_files(path = relfn





					#if 

					#new_fi.sources = fi.sources.union(set([self.id()]))

					## Either content or sources changed
					#if new_fi.content_id != fi.content_id or new_fi.sources != fi.sources:
						#if new_fi.content_id != fi.content_id:
							#logging.info('updated content: {}'.format(relfn))
						#if new_fi.sources != fi.sources:
							#logging.info('updated sources: {}'.format(relfn))
						#new_fi.action = 'updated'
						#c.add_file(relfn, new_fi)
						#changed = True

				#elif not fi:
					## Haven't seen that file before at all,
					#if not rule.commit_untracked:
						#logging.debug('ignoring untracked file {}'.format(relfn))
						#continue

					#new_fi.sources.add(self.id())
					#logging.info('created {}'.format(relfn))
					#new_fi.action = 'created'
					#c.add_file(relfn, new_fi)
					#changed = True

		## Handle file deletions.
		## A file is considered deleted if it has been marked in the history as
		## present in this repository instance but can not be found in the
		## filesystem anymore.
		#unseen_files = set(c.get_filenames()).difference(seen_files)
		#for fn in unseen_files:
			#fi = c.get_file(fn)
			#if self.id() in fi.sources:
				#new_fi = fi.copy()
				#new_fi.sources.discard(self.id())
				#if not new_fi.sources:
					#logging.info('exterminated "{}" (no sources left)'.format(relfn))
					#c.delete_file(relfn)
				#else:
					#logging.info('deleted "{}" ({} sources left)'.format(relfn, len(new_fi.sources)))
					#c.edit_file(relfn, new_fi)
				#changed = True

		#if changed:
			#commit_id = self.history.save_commit(c)
			#self.history.set_head_id(commit_id)
		#else:
			#logging.info('nothing to commit')

	def commit_(self):
		"""
		Commit the working dir state to the history, moving HEAD.
		"""
		c = self.history.create_commit(on_top = True, copy = True)

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
	# File utiliity functions
	#
	def compute_content_id(self, relfn):
		hash_ = HashlibHasher('sha256').hash
		return hash_(open(self.harmony_dir(relfn), 'rb'))

	#
	# Remotes
	# 
	
	def get_remote(self, remote_id, allow_nickname = True):
		"""
		Return the remote with the given id
		"""
		#self.load_remotes()
		remotes = self.configuration.get_remotes()
		#logging.debug("i know these remotes:" + str(remotes.keys()))
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
				conflicts, commit_id, commit = self.create_merge_commit(
						base_id = lowest_common_ancestor,
						local_id = myhead,
						remote_id = remote_head_id)

				assert (len(conflicts) == 0) or (commit_id is None)

				if conflicts:
					logging.info("Automatic merge failed.")
					for conflict in conflicts:
						logging.info("Conflict: " + conflict)

				if commit_id is None and not conflicts:
					commit_id = self.history.save_commit(commit)
					
				logging.info("Merge.")
				return conflicts, commit_id
			
		finally:
			os.unlink(tmpfilename)
	
	def create_merge_commit(self, base_id, local_id, remote_id):
		"""
		Create a merge commit.

		@param base_id common ancestor of the two merge paths
		@param local_id commit at the tip of the path considered 'local'
		@param remote_id commit at the tip of the path considered 'remote'

		@return tuple (conflicts, commit_id, commit).

		If the merge is a fast-forward, conflicts is an empty collection,
		commit_id is one of (local_id, remote_id) and commit holds the
		according commit data.

		If the merge is non-fast-forward, conflicts is a (possibly empty)
		collection of filenames of all files for which the user has to choose
		a new default version, commit_id is None and commit contains a
		preliminary commit object (missing default versions for the
		conflicting file names).
		"""
		logging.debug('merge(\n\tbase={}\n\tlocal={}\n\tremote={}\n)'.format(
			base_id, local_id, remote_id))

		base = self.history.get_commit(base_id)
		local = self.history.get_commit(local_id)
		remote = self.history.get_commit(remote_id)
		
		conflicts = []
		merge = Commit(self)
		merge.set_parents({local_id: local, remote_id: remote})

		# Is this a fast-forward?
		c, comparisons = local.compare_clock(remote)
		if c in (-1, 0, 1):
			top = (local_id, local)
			if c == -1:
				top = (remote_id, remote)
			logging.info('Merge: This is a fast-forward.')
			return ([], top[0], top[1])

		all_filenames = frozenset(local.get_filenames()).union(remote.get_filenames())

		for filename in all_filenames:
			remotes_for_file = frozenset().union(*[set(d.keys()) for cid,d in local.get_file_versions(filename).items()])

			# TODO: Move this to a commit.check_sanity() method

			# remotes_for_file should be completely covered by comparisons
			# keys
			print(remotes_for_file)
			print(set(comparisons.keys()))
			assert remotes_for_file.issubset(set(comparisons.keys()))

			# Merge commit unifies the most up to date file versions from both
			# commits (depending on their clock value)
			for remote_id in remotes_for_file:
				source_commit = local
				if comparisons[remote_id] == -1:
					source_commit = remote

				source_cid = source_commit.get_file_content_by_repo(filename, remote_id)
				merge.add_source(filename, source_cid, remote_id)

			# New decide the default version.
			# If both repos agree, there is no problem
			local_default = local.get_default_version(filename)
			remote_default = remote.get_default_version(filename)
			base_default = base.get_default_version(filename)

			cids = set(merge.get_file_versions(filename).keys())

			if local_default == remote_default:
				merge.set_default_version(filename, local_default)
			elif local_default == base_default or (local_default not in cids):
				merge.set_default_version(filename, remote_default)
			elif remote_default == base_default or (remote_default not in cids):
				merge.set_default_version(filename, local_default)
			else:
				conflicts.append(filename)	

		return conflicts, None, merge
	
	def clone(self, uri):
		"""
		Clone the repository state (history) at uri to the local working directory.

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
		
	#def get_sources(self, relpath):
		#"""
		#Return a list of all remotes that are currently believed to contain a
		#copy of the file specified by relpath.
		#"""
		#cid = self.history.get_head_id()
		#if cid is not None:
			#c = self.history.get_commit(cid)
			#f = c.get_file(relpath)
			#if f is not None:
				#return f.sources
		#return []
	
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
			
	def get(self, relpath, repository_ids = None, cid = None):
		"""
		
		Retrieve the file at relpath from the given repository in the
		specified version to the working directory.

		@param relpath Relative path of the file to retrieve.
		@param repository_ids IDs of repositories to try to retrieve from, if empty
			or None, use the HEAD commit to find a repository holding the file.
		@param cid Content ID of the file version to retrieve. If None, use
			the HEAD commits default version of the file.

		"""

		if cid is None:
			hid = self.history.get_head_id()
			if hid is not None:
				h = self.history.get_commit(hid)
				cid = h.get_default_version(relpath)

		assert cid is not None, 'No cid specified and no default version available'



		if not repository_ids:
			hid = self.history.get_head_id()
			if hid is not None:
				h = self.history.get_commit(hid)
				repository_ids = h.get_repos_providing(relpath, cid)

		#assert repository_ids is not None and len(repository_ids), 'No repositories to pull file from'
			
		for src in repository_ids:
			logging.debug('checking whether {} is available from {}'.format(relpath, src))
			remote = self.get_remote(src)

			if remote is None:
				logging.warning('no info available about remote {}, ignoring'.format(src))
				continue

			remote.pull_file(relpath)
			new_head = self.commit()
			
			#if remote.is_writeable():
				#remote.push_history()
				#remote.add_remote_head(new_head)
			#else:
				#logging.warning('remote {} is not writable, the other end will not realize we have a copy until it pulls from us!'.format(str(remote)))
				
				
			return
		logging.error('no remote found to provide {}'.format(relpath))
	
	def available_files(self):
		"""
		Return all files that were known/assumed
		to exist in the latest commit (HEAD) in this repository.
		"""
		head = self.history.get_head()
		if head:
			return list(head.get_filenames_for_source(self.id()))
		else:
			return []
	
	def cmd_log(self):
		h = self.get_history()
		for cid, commit in h:
			ps = tuple(commit.get_parents().keys())
			print('commit {:8s} parents {:8s} {:8s}'.format(
				cid[-8:],
				ps[0][-8:] if len(ps) >= 1 else '',
				ps[1][-8:] if len(ps) >= 2 else ''
			))
			
			print('created {:%Y-%m-%d %H:%M} in {}'.format(commit.created,
				commit.repository_id))
			
			#for p in commit.parents:
				#print("  p {}".format(p[-8:]))
				
			if len(ps) == 0:
				print('  TODO: commit diff not implemented yet')
				#for filename in commit.get_filenames():
					#f = commit.get_file(filename)
					#print('  I {} {}:...{:8s}'.format(
						#filename, f.content_id.split(':')[0],
						#f.content_id.split(':')[1][-8:]))
			elif len(ps) == 1:
				# TODO: this unecessarily reads the parent commit from disk
				# (do we care?).
				print('  TODO: commit diff not implemented yet')
				#d = CommitDifference(self.history.get_commit(ps[0]), commit)
				#for change in d.get_changes():
					#print('  {}'.format(change.brief()))
			elif len(ps) == 2:
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
	
	
