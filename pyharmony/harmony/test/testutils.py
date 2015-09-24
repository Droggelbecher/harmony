
import tempfile
import shutil
import os
import os.path

KEEP_TEMPDIRS = True

class TempDir:
    def __init__(self):
        self.path = tempfile.mkdtemp(prefix='harmony-test-tmp')

    def __enter__(self):
        return self.path

    def __exit__(self, exc, value, tb):
        if not KEEP_TEMPDIRS:
            shutil.rmtree(self.name)

def mkdir(*args):
    os.makedirs(os.path.join(*args), exist_ok=True)


