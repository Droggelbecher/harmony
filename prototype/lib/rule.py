
import fnmatch

class Rule:
    def __init__(self, **kws):
        self.commit_tracked = True
        self.commit_untracked = True
        self.commit_nonlocal_tracked = False
        self.ignore = False
        self.match_filename = None

        self.__dict__.update(kws)
        
        self.make_sane()
    
    def make_sane(self):
        if self.ignore:
            self.commit_tracked = False
            self.commit_untracked = False
            self.commit_nonlocal_tracked = False

    def match(self, repository, fn):
        if self.match_filename is not None and fnmatch.fnmatch(fn, self.match_filename):
            return True
        return False


# vim: set ts=4 sw=4 expandtab:
