
import logging

class Change:
    old_filename = None
    new_filename = None
    
    def get_target(self):
        return self.new_filename
    
    def get_source(self):
        return self.old_filename
    
    def __lt__(self, other):
        return (self.old_filename, self.new_filename) < (other.old_filename, other.new_filename)

class Edit(Change):
    def __init__(self, filename, fi2):
        self.new_filename = filename
        self.new_fileinfo = fi2
        
    def brief(self):
        return 'M {} {}:{:8s}...'.format(
                self.new_filename,
                self.new_fileinfo.content_id.split(':')[0],
                self.new_fileinfo.content_id.split(':')[1][:8])

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
        return 'A {} {}:{:8s}...'.format(
                self.new_filename,
                self.new_fileinfo.content_id.split(':')[0],
                self.new_fileinfo.content_id.split(':')[1][:8])
        
class Rename(Change):
    def __init__(self, filename, filename2, fi2):
        self.old_filename = filename
        self.new_filename = filename2
        self.new_fileinfo = fi2

    def brief(self):
        return 'R {} => {}'.format(self.old_filename, self.new_filename) 
    
class CommitDifference:

    """
    Represents the difference between the states induced by two commits c1 and
    c2.
    """

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
        """
        Compute the difference, that is the set of changes necessary to turn
        state c1 into state c2 (as given in __init__).
        This method is called automatically from __init__.
        """
        
        c1 = self.c1_
        c2 = self.c2_
    
        filenames_c1 = set(c1.get_filenames())
        filenames_c2 = set(c2.get_filenames())
        filenames_base = filenames_c1.intersection(filenames_c2)
        unhandled_c1 = filenames_c1.difference(filenames_base)
        unhandled_c2 = filenames_c2.difference(filenames_base)

        # Filename present in both AND contents differ ---> EDIT
        for filename in filenames_base:
            fi1 = c1.get_file(filename)
            fi2 = c2.get_file(filename)
            if fi1.content_id != fi2.content_id:
                self.add_change(Edit(filename, fi2))
                
        # Filename only in c1 AND
        # some new files in c2 with same content
        # ----> RENAME
        #
        # Filename only in c1 AND
        # content not in c2
        # ----> DELETION
        for filename in unhandled_c1:
            cid = c1.get_file(filename).content_id
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
        #logging.debug("get_changes_by_source")
        for c in self.changes_:
            t = c.get_source()
            if t is not None:
                #logging.debug("d[{}] = {}".format(t, c))
                assert t not in d
                d[t] = c
        return d
    
    def __add__(self, other):
        r = CommitDifference(self.c1_, self.c2_)
        r.changes_ = self.changes_ + other.changes_
        return r
    
    def __getitem__(self, key): return self.changes_.__getitem__(key)
    def __setitem__(self, key): return self.changes_.__setitem__(key)

