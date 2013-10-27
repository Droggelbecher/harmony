

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

class TestRepository(unittest.TestCase):
	
	def test_lca(self):
		a = Commit()
		b = Commit()
		c = Commit()
		
		self.assertEqual(a.lca(a), a)
		
		a.parents.add(b)
		self.assertEqual(a.lca(a), a)
		self.assertEqual(a.lca(b), b)
		self.assertEqual(b.lca(a), b)
		self.assertEqual(b.lca(b), b)
		
		b.parents.add(c)
		self.assertEqual(a.lca(a), a)
		self.assertEqual(a.lca(b), b)
		self.assertEqual(b.lca(a), b)
		self.assertEqual(b.lca(b), b)
		
		self.assertEqual(a.lca(c), c)
		self.assertEqual(b.lca(c), c)
		self.assertEqual(c.lca(c), c)
		
		# TODO: multiple parents, diamonds, etc...
		
	def test_merge(self):
		a = Commit()
		b = Commit()
		c, conflicts = a.merge(b)
		self.assertEqual(len(conflicts), 0)
		self.assertEqual(set(c.parents), set((a, b)))
		
		a = Commit()
		fia = FileInfo(BytesIO(b"This is foo.txt"))
		a.add_file('a.txt', fia)
		
		b = Commit()
		fib = FileInfo(BytesIO(b"This is bar.txt"))
		b.add_file('b.txt', fib)
		
		c, conflicts = a.merge(b)
		self.assertEqual(len(conflicts), 0)
		self.assertEqual(set(c.parents), set((a, b)))
		self.assertEqual(c.files['a.txt'], fia)
		self.assertEqual(c.files['b.txt'], fib)
	
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
			commandline.run_command(['init'])
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
			commandline.run_command(['pull'])
			commandline.run_command(['get', 'example.txt'])
			self.check_file(tmpdir3, 'example.txt', 'This is a different text.')

if __name__ == '__main__':
	logging.basicConfig(level = logging.DEBUG, format = '[{levelname:7s}] {message:s}', style = '{')
	unittest.main()

