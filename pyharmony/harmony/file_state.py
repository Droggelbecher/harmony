
class FileState:

    # TODO: automatically normalize path. Either on string level or
    # ask WorkingDirectory to do it when creating these

    def __init__(self, path = None, digest = None, size = None, mtime = None):
        self.path = path
        self.digest = digest
        self.size = size
        self.mtime = mtime

    def contents_different(self, other):
        return self.size != other.size or self.digest != other.digest



