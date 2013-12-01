
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
import sys
from repository import Repository

class TestRepository(unittest.TestCase):
	
	def allfiles(self, directory):
		r = []
		for root, dirs, files in os.walk(directory):
			for f in files:
				abspath = os.path.join(root, f)
				relpath = os.path.relpath(os.path.abspath(abspath), os.path.abspath(directory))
				r.append(relpath)
		return sorted(r)
	
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
			
	def test_init(self):
		expected_files_after_init = sorted([
				'.harmony/config',
				'.harmony/remotes'
		])
		
		#
		# 'init' creates exactly the expected files
		#
		
		with tempfile.TemporaryDirectory() as tmpdir:
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
		with tempfile.TemporaryDirectory() as tmpdir1, \
				tempfile.TemporaryDirectory() as tmpdir2:
			os.chdir(tmpdir1)
			commandline.run_command(['init'])
			
			os.chdir(tmpdir2)
			commandline.run_command(['clone', tmpdir1])
			
	def test_get(self):
		#
		# Get works (locally)
		# 
		with tempfile.TemporaryDirectory() as tmpdir1, \
				tempfile.TemporaryDirectory() as tmpdir2:
			os.chdir(tmpdir1)
			commandline.run_command(['init'])
			self.create_file(tmpdir1, 'example.txt', 'This is an example.')
			commandline.run_command(['commit'])
			
			os.chdir(tmpdir2)
			commandline.run_command(['clone', tmpdir1])
			commandline.run_command(['get', 'example.txt'])
			self.check_file(tmpdir2, 'example.txt', 'This is an example.')
			
		#
		# Get will get the newest version of a file
		# 
		with tempfile.TemporaryDirectory() as tmpdir1, \
				tempfile.TemporaryDirectory() as tmpdir2, \
				tempfile.TemporaryDirectory() as tmpdir3:
					
			os.chdir(tmpdir1)
			commandline.run_command(['init', '--name', 'repo1'])
			self.create_file(tmpdir1, 'example.txt', 'This is an example.')
			commandline.run_command(['commit'])
			
			os.chdir(tmpdir2)
			commandline.run_command(['clone', tmpdir1])
			commandline.run_command(['get', 'example.txt'])
			self.check_file(tmpdir2, 'example.txt', 'This is an example.')
			
			os.chdir(tmpdir3)
			commandline.run_command(['clone', tmpdir2])
			commandline.run_command(['get', 'example.txt'])
			self.check_file(tmpdir2, 'example.txt', 'This is an example.')
			
			os.chdir(tmpdir1)
			self.create_file(tmpdir1, 'example.txt', 'This is a different text.')
			commandline.run_command(['commit'])
			
			os.chdir(tmpdir3)
			
			logging.debug(self.allfiles(tmpdir3))
			
			commandline.run_command(['pull-state', 'repo1'])
			commandline.run_command(['get', 'example.txt'])
			self.check_file(tmpdir3, 'example.txt', 'This is a different text.')

	def test_merge(self):
		
		# Case 1: adding files on both sides leads to the union of files
		# being available in the merged directory
		with tempfile.TemporaryDirectory() as tmpdir1, \
				tempfile.TemporaryDirectory() as tmpdir2, \
				tempfile.TemporaryDirectory() as tmpdir3:
					
			os.chdir(tmpdir1)
			commandline.run_command(['init', '--name', 'repo1'])
			self.create_file(tmpdir1, 'base.txt', 'This is an example.')
			commandline.run_command(['commit'])
			
			os.chdir(tmpdir2)
			commandline.run_command(['clone', tmpdir1])
			self.create_file(tmpdir2, 'dir2.txt', 'Foo.')
			commandline.run_command(['commit'])
			
			os.chdir(tmpdir1)
			self.create_file(tmpdir1, 'dir1.txt', 'Bar.')
			commandline.run_command(['commit'])
			
			os.chdir(tmpdir2)
			commandline.run_command(['pull-state', 'repo1'])
			commandline.run_command(['log'])
			
			r = Repository(tmpdir1)
			self.assertIn('base.txt', r.available_files())
			self.assertIn('dir1.txt', r.available_files())
			self.assertNotIn('dir2.txt', r.available_files())
			
			self.assertIn('base.txt', self.allfiles(tmpdir1))
			self.assertIn('dir1.txt', self.allfiles(tmpdir1))
			self.assertNotIn('dir2.txt', self.allfiles(tmpdir1))
			
			r = Repository(tmpdir2)
			self.assertIn('base.txt', r.available_files())
			self.assertIn('dir1.txt', r.available_files())
			self.assertIn('dir2.txt', r.available_files())
			
			self.assertNotIn('base.txt', self.allfiles(tmpdir2))
			self.assertNotIn('dir1.txt', self.allfiles(tmpdir2))
			self.assertIn('dir2.txt', self.allfiles(tmpdir2))
			
	def test_rm(self):
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
		
if __name__ == '__main__':
	logging.basicConfig(level = logging.DEBUG, format = '[{levelname:7s}] {message:s}', style = '{')
	unittest.main()

# vim: set ts=4 sw=4 tw=78 noexpandtab :

