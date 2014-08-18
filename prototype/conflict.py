
class Conflict:
	def __init__(self, type_, filename, l, r):
		self.type_ = type_
		self.filename = filename
		self.local_change = l
		self.remote_change = r
		
	def __str__(self):
		return '''{} conflict for {}:
local change:  {}
remote change: {}'''.format(self.type_, self.filename,
		self.local_change.brief(),
		self.remote_change.brief())


