#!/usr/bin/env python
import sys
sys.path.append('lib/')

import random
import unittest
import logging
from commit import Commit
from io import StringIO
from io import BytesIO
from file_info import FileInfo
import os
import os.path
import tempfile
import commandline
from repository import Repository

KEEP_TEMPDIRS = True

class TempDir:
	def __init__(self):
		self.tempdir = tempfile.TemporaryDirectory()

	def __enter__(self):
		if KEEP_TEMPDIRS:
			return tempfile.mkdtemp(prefix='harmony-test-tmp')
		else:
			return self.tempdir.__enter__()

	def __exit__(self, exc, value, tb):
		if KEEP_TEMPDIRS:
			pass
		else:
			return self.tempdir.__exit__(exc, value, tb)

class TestRepository(unittest.TestCase):
	
	# Some convenience method to enhance
	# readability of tests

	def cd(self, d): os.chdir(d)
	def rm(self, fn): os.remove(fn)
	def harmony(self, *args): commandline.run_command(args)

	def allfiles(self, directory):
		r = []
		for root, dirs, files in os.walk(directory):
			for f in files:
				abspath = os.path.join(root, f)
				relpath = os.path.relpath(os.path.abspath(abspath), os.path.abspath(directory))
				r.append(relpath)
		return sorted(r)

	def assert_in_dir(self, fn, d): self.assertIn(fn, self.allfiles(d))
	def assert_in_repo(self, fn, d): self.assertIn(fn, Repository(d).available_files())
	def assert_not_in_dir(self, fn, d): self.assertNotIn(fn, self.allfiles(d))
	def assert_not_in_repo(self, fn, d): self.assertNotIn(fn, Repository(d).available_files())
	
	def create_file(self, dirname, fname, content = ''):
		with open(os.path.join(dirname, fname), 'w') as f:
			f.write(content)
			
	def check_file(self, dirname, fname, content = ''):
		path = os.path.join(dirname, fname)
		print(path)
		self.assertTrue(os.path.exists(path))
		self.assertTrue(os.path.isfile(path))
		with open(path, 'r') as f:
			self.assertEqual(f.read(), content)

	#def tmpdir(self): return tempfile.TemporaryDirectory()

	#
	# Actual tests
	#

			
	def test_init(self):
		expected_files_after_init = sorted([
				'.harmony/config',
				'.harmony/remotes',
				'.harmony/rules'
		])
		
		#
		# 'init' creates exactly the expected files
		#
		
		with TempDir() as tmpdir:
			os.chdir(tmpdir)
			commandline.run_command(['init'])
			self.assertEqual(self.allfiles(tmpdir), expected_files_after_init)
		
		expected = sorted(
				expected_files_after_init +
				[ 'foo.txt', 'bar.txt' ]
		)
		
		#
		# Pre-existing files are untouched and do not
		# trigger additional file creation
		# 
		
		with tempfile.TemporaryDirectory() as tmpdir:
			os.chdir(tmpdir)
			self.create_file(tmpdir, 'foo.txt', 'tach')
			self.create_file(tmpdir, 'bar.txt')
			
			commandline.run_command(['init'])
			self.assertEqual(self.allfiles(tmpdir), expected)
		
		#
		# A second init in the same directory fails
		# 
		
		with tempfile.TemporaryDirectory() as tmpdir:
			os.chdir(tmpdir)
			commandline.run_command(['init'])
			with self.assertRaises(FileExistsError):
				commandline.run_command(['init'])
				
	def test_clone(self):
		#with tempfile.TemporaryDirectory() as tmpdir1, \
				#tempfile.TemporaryDirectory() as tmpdir2:
		with TempDir() as tmpdir1, \
				TempDir() as tmpdir2:
			os.chdir(tmpdir1)
			commandline.run_command(['init'])
			
			os.chdir(tmpdir2)
			commandline.run_command(['clone', tmpdir1])
			
	def test_get_01(self):
		#
		# Get works (locally)
		 
		with TempDir() as tmpdir1, \
				TempDir() as tmpdir2:
			os.chdir(tmpdir1)
			commandline.run_command(['init'])
			self.create_file(tmpdir1, 'example.txt', 'This is an example.')
			commandline.run_command(['commit'])
			
			os.chdir(tmpdir2)
			commandline.run_command(['clone', tmpdir1])
			commandline.run_command(['get', 'example.txt'])
			self.check_file(tmpdir2, 'example.txt', 'This is an example.')

			# tmpdir2 should now be aware that example.txt is available in
			# both repos with the same version
			r1 = Repository(tmpdir1)
			r2 = Repository(tmpdir2)

			self.assertEqual(
				set(
					r2.head() \
					.get_file_versions('example.txt') \
					['sha256:4e2fc0c58f973ddd4ace0de85a5ebba9b88cc35df80d8c455c6079726075d3bf'] \
					.keys()
					),
				set(
					(r1.id(), r2.id())
					)
				)
					#['sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'] \

			#assert_file_version(tmpdir2, 'example.txt',
					#'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',


	def test_get_02(self):
		#
		# Get will get the newest version of a file
		# 
		with TempDir() as tmpdir1, \
				TempDir() as tmpdir2, \
				TempDir() as tmpdir3:
					
			print("tmpdir1=", tmpdir1)
			print("tmpdir2=", tmpdir2)
			print("tmpdir3=", tmpdir3)

			os.chdir(tmpdir1)
			commandline.run_command(['init', '--name', 'repo1'])
			self.create_file(tmpdir1, 'example.txt', 'This is an example.')
			commandline.run_command(['commit'])
			
			#os.chdir(tmpdir2)
			#commandline.run_command(['clone', tmpdir1])
			#commandline.run_command(['get', 'example.txt'])
			#self.check_file(tmpdir2, 'example.txt', 'This is an example.')
			
			os.chdir(tmpdir3)
			commandline.run_command(['clone', tmpdir1])
			commandline.run_command(['get', 'example.txt'])
			self.check_file(tmpdir3, 'example.txt', 'This is an example.')
			
			os.chdir(tmpdir1)
			self.create_file(tmpdir1, 'example.txt', 'This is a different text.')
			commandline.run_command(['commit'])
			
			os.chdir(tmpdir3)
			
			logging.debug(self.allfiles(tmpdir3))
			
			commandline.run_command(['pull-state', 'repo1'])
			commandline.run_command(['get', 'example.txt'])
			self.check_file(tmpdir3, 'example.txt', 'This is a different text.')

	def test_merge(self):
		logging.debug("----- test merge")
		
		cd = self.cd
		harmony = self.harmony
		create = self.create_file

		# Case 1: adding files on both sides leads to the union of files
		# being available in the merged directory
		with TempDir() as tmpdir1, \
				TempDir() as tmpdir2, \
				TempDir() as tmpdir3:

			cd(tmpdir1)
			harmony('init', '--name', 'repo1')
			create(tmpdir1, 'base.txt', 'This is an example.')
			harmony('commit')

			cd(tmpdir2)
			harmony('clone', tmpdir1)
			create(tmpdir2, 'dir2.txt', 'Foo.')
			harmony('commit')

			cd(tmpdir1)
			create(tmpdir1, 'dir1.txt', 'Bar.')
			harmony('commit')

			cd(tmpdir2)
			harmony('pull-state', 'repo1')
			harmony('log')

			r = Repository(tmpdir1)
			self.assertIn('base.txt', r.available_files())
			self.assertIn('dir1.txt', r.available_files())
			self.assertNotIn('dir2.txt', r.available_files())
			
			self.assertIn('base.txt', self.allfiles(tmpdir1))
			self.assertIn('dir1.txt', self.allfiles(tmpdir1))
			self.assertNotIn('dir2.txt', self.allfiles(tmpdir1))
			
			r = Repository(tmpdir2)
			self.assertNotIn('base.txt', r.available_files())
			self.assertNotIn('dir1.txt', r.available_files())
			self.assertIn('dir2.txt', r.available_files())
			
			self.assertNotIn('base.txt', self.allfiles(tmpdir2))
			self.assertNotIn('dir1.txt', self.allfiles(tmpdir2))
			self.assertIn('dir2.txt', self.allfiles(tmpdir2))
			
	def test_rm_01(self):
		"""
		Harmony can decide cleanly between the following file states:
		
		(a) not tracked: The file is not tracked at all. An appearance in the
		working directory will lead to an addition into the repository.
		
		(b) not here: The file is not present in the local copy, but
		its known to the repository.
		An appearance in the working dir will most likely result in a merge
		conflict.
		
		(c) removed: The file should be there locally, but was removed from
		the working dir.
		This will lead to the file becoming locally untracked and, if it was
		the last copy, completely untracked.
		"""
		
		# 
		# Singe repository instance,
		# create a file, commit, delete it, commit again.
		# The file should not appear in the list of tracked files anymore.
		#
		with TempDir() as D1:
			
			self.cd(D1)
			self.harmony('init', '--name', 'repo1')
			self.create_file(D1, 'hellogoodbye.txt', 'You say yes, I say no.')
			self.harmony('commit')
			
			self.assert_in_dir('hellogoodbye.txt', D1)
			self.assert_in_repo('hellogoodbye.txt', D1)

			self.rm('hellogoodbye.txt')
			self.assert_not_in_dir('hellogoodbye.txt', D1)
			self.assert_in_repo('hellogoodbye.txt', D1)

			self.harmony('commit')
			self.assert_not_in_dir('hellogoodbye.txt', D1)
			self.assert_not_in_repo('hellogoodbye.txt', D1)

	#def test_rm_02(self):
		## Two repo instances,
		## create file, commit, sync, delete, commit again.
		## The file should still be considered tracked with 1 source.
		##
		## That is, get reports to the repo it copied from!
		##
		#with TempDir() as D1, TempDir() as D2:

			#self.cd(D1)
			#self.harmony('init', '--name', 'repo1')
			#self.create_file(D1, 'hellogoodbye.txt', 'You say yes, I say no.')
			#self.harmony('commit')
			
			#self.assert_in_dir('hellogoodbye.txt', D1)
			#self.assert_in_repo('hellogoodbye.txt', D1)

			#self.cd(D2)
			#self.harmony('clone', D1)
			#self.harmony('get', 'hellogoodbye.txt')
			#self.check_file(D2, 'hellogoodbye.txt', 'You say yes, I say no.')
			
			#self.assert_in_dir('hellogoodbye.txt', D2)
			#self.assert_in_repo('hellogoodbye.txt', D2)

			#self.cd(D1)
			#self.rm('hellogoodbye.txt')
			#self.assert_not_in_dir('hellogoodbye.txt', D1)
			#self.assert_in_repo('hellogoodbye.txt', D1)

			#self.harmony('commit')
			#self.assert_not_in_dir('hellogoodbye.txt', D1)
			#self.assert_not_in_repo('hellogoodbye.txt', D1)

			#self.harmony('get', 'hellogoodbye.txt')
			#self.assert_in_dir('hellogoodbye.txt', D1)
			#self.assert_in_repo('hellogoodbye.txt', D1)
			
		
if __name__ == '__main__':
	logging.basicConfig(level = logging.DEBUG, format = '[{levelname:7s}] {message:s}', style = '{')
	unittest.main()

# vim: set ts=4 sw=4 tw=78 noexpandtab :

