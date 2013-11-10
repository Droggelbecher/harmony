
class Change:
	old_filename = None
	new_filename = None
	
	def get_target(self):
		return self.new_filename
	
	def get_source(self):
		return self.old_filename

class Edit(Change):
	def __init__(self, filename, fi2):
		self.new_filename = filename
		self.new_file_info = fi2
		
	def brief(self):
		return 'M {}'.format(self.new_filename) 

class Deletion(Change):
	def __init__(self, filename):
		self.old_filename = filename
		self.new_filename = filename
		
	def brief(self):
		return 'D {}'.format(self.new_filename) 

class Creation(Change):
	def __init__(self, filename, fi):
		self.new_filename = filename
		self.new_fileinfo = fi
		
	def brief(self):
		return 'A {}'.format(self.new_filename) 
		
class Rename(Change):
	def __init__(self, filename, filename2, fi2):
		self.old_filename = filename
		self.new_filename = filename2
		self.new_fileinfo = fi2

	def brief(self):
		return 'R {} => {}'.format(self.old_filename, self.new_filename) 
	
class CommitDifference:
	def __init__(self, c1, c2):
		self.c1_ = c1
		self.c2_ = c2
		self.changes_ = []
		self.compute()
	
	def add_change(self, change):
		self.changes_.append(change)
		
	def get_changes(self):
		return self.changes_
		
	def compute(self):
		c1 = self.c1_
		c2 = self.c2_
	
		filenames_c1 = set(c1.get_filenames())
		filenames_c2 = set(c2.get_filenames())
		filenames_base = filenames_c1.intersection(filenames_c2)
		unhandled_c1 = filenames_c1.difference(filenames_base)
		unhandled_c2 = filenames_c2.difference(filenames_base)
		
		for filename in filenames_base:
			fi1 = c1.get_file(filename)
			fi2 = c2.get_file(filename)
			if fi1.content_id != fi2.content_id:
				self.add_change(Edit(filename, fi2))
				
		for filename in unhandled_c1:
			c1.get_file(filename).content_id
			# is there a new file in c2 with this content id?
			fnames = c2.get_by_content_id(cid).difference(c1.get_filenames())
			if fnames:
				filename2 = fnames.pop()
				self.add_change(Rename(filename, filename2, c2.get_file(filename2)))
				unhandled_c2.discard(filename2)
			else:
				self.add_change(Deletion(filename))
				
		for filename in unhandled_c2:
			self.add_change(Creation(filename, c2.get_file(filename)))
			
	
	def get_changes_by_target(self):
		d = {}
		for c in self.changes_:
			t = c.get_target()
			assert t not in d
			d[t] = c
		return d
	
	def get_changes_by_source(self):
		d = {}
		for c in self.changes_:
			t = c.get_source()
			assert t not in d
			d[t] = c
		return d
	
	def __add__(self, other):
		r = CommitDifference(self.c1_, self.c2_)
		r.changes_ = self.changes_ + other.changes_
		return r

