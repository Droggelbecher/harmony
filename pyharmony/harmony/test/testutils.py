
import tempfile
import shutil
import os
import os.path
import unittest

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

def echo(s, *args):
    filename = os.path.join(*args)
    with open(filename, 'w') as f:
        f.write(s)

class TestCase(unittest.TestCase):
    def assertFileExists(self, *args, msg=''):
        filename = os.path.join(*args)
        if not os.path.exists(filename):
            self.fail('{} does not exist although it should. {}'.format(filename, msg))

    def assertDirectoriesEqual(self, dir1, dir2, msg='', failure_base=None):

        if failure_base is None:
            failure_base = '{} and {} unqual dirs'.format(dir1, dir2)

        if not os.path.isdir(dir1):
            self.fail('{}: {} is not a directory.'.format(failure_base, dir1))
        if not os.path.isdir(dir2):
            self.fail('{}: {} is not a directory.'.format(failure_base, dir2))

        files_dir1 = set(os.listdir(dir1))
        files_dir2 = set(os.listdir(dir2))

        if files_dir1 != files_dir2:
            self.fail('{}: filelists of {} and {} do not match.'.format(failure_base, dir1, dir2))

        directories = [f for f in files_dir1 if os.path.isdir(os.path.join(dir1, f))]
        for directory in directories:
            self.assertDirectoriesEqual(
                    os.path.join(dir1, directory),
                    os.path.join(dir2, directory),
                    msg = msg,
                    failure_base = failure_base
                    )

        files = [f for f in files_dir1 if os.path.isfile(os.path.join(dir1, f))]
        for filename in files:
            self.assertFileContentsEqual(
                    os.path.join(dir1, filename),
                    os.path.join(dir2, filename),
            )
                    

    def assertFileContentsEqual(self, filename1, filename2, msg=''):
        with open(filename1, 'r') as f1, open(filename2, 'r') as f2:
            s1 = f1.read()
            s2 = f2.read()
            self.assertEqual(s1, s2, msg)

