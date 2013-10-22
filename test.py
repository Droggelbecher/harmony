

import random
import unittest
from repository_state import RepositoryState
from io import StringIO
from io import BytesIO
from file_info import FileInfo

class TestRepository(unittest.TestCase):
	
	def test_lca(self):
		a = RepositoryState()
		b = RepositoryState()
		c = RepositoryState()
		
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
		a = RepositoryState()
		b = RepositoryState()
		c, conflicts = a.merge(b)
		self.assertEqual(len(conflicts), 0)
		self.assertEqual(set(c.parents), set((a, b)))
		
		a = RepositoryState()
		fia = FileInfo(BytesIO(b"This is foo.txt"))
		a.add_file('a.txt', fia)
		
		b = RepositoryState()
		fib = FileInfo(BytesIO(b"This is bar.txt"))
		b.add_file('b.txt', fib)
		
		c, conflicts = a.merge(b)
		self.assertEqual(len(conflicts), 0)
		self.assertEqual(set(c.parents), set((a, b)))
		self.assertEqual(c.files['a.txt'], fia)
		self.assertEqual(c.files['b.txt'], fib)
		
		

if __name__ == '__main__':
	unittest.main()

