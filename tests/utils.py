
import tempfile
import shutil
import os
import os.path
import unittest
import warnings

from pathlib import Path

KEEP_TEMPDIRS = True

class TempDir:
    def __init__(self):
        self.path = Path(tempfile.mkdtemp(prefix='harmony-test-tmp')).resolve()

    def __enter__(self):
        return self.path

    def __exit__(self, exc, value, tb):
        if not KEEP_TEMPDIRS:
            shutil.rmtree(self.name)


def directories_equal(dir1, dir2, msg='', failure_base=None):

    dir1 = Path(dir1)
    dir2 = Path(dir2)

    if failure_base is None:
        failure_base = '{} and {} unqual dirs'.format(dir1, dir2)

    if not dir1.is_dir() or not dir2.is_dir():
        return False

    files_dir1 = set(f.name for f in dir1.iterdir())
    files_dir2 = set(f.name for f in dir2.iterdir())

    if files_dir1 != files_dir2:
        s = '''{}: filelists of
{}
and
{}
do not match.
In both:
{}
In first but not second:
{}
In second but not first:
{}
'''.format(failure_base, dir1, dir2,
       '  ' + ('\n  '.join(str(f) for f in (files_dir1 & files_dir2)) or '(None)'),
       '  ' + ('\n  '.join(str(f) for f in (files_dir1 - files_dir2)) or '(None)'),
       '  ' + ('\n  '.join(str(f) for f in (files_dir2 - files_dir1)) or '(None)'),
      )
        warnings.warn(s)
        return False

    directories = [f for f in files_dir1 if (dir1 / f).is_dir()]
    for directory in directories:
        r = directories_equal(
                dir1 / directory,
                dir2 / directory,
                msg = msg,
                failure_base = failure_base
                )
        if not r:
            return False

    files = [f for f in files_dir1 if (dir1 / f).is_file()]
    for filename in files:
        if (dir1 / filename).read_bytes() != (dir2 / filename).read_bytes():
            s = '''{}: file contents of
{}
and
{}
differ.

--- {}
{}

--- {}
{}
'''.format(failure_base, dir1 / filename, dir2 / filename,
    (dir1 / filename), (dir1 / filename).read_text(), 
    (dir2 / filename), (dir2 / filename).read_text(),
    )
            warnings.warn(s)
            return False

    return True


class TestCase(unittest.TestCase):

    def assertFilesEqual(self, a, b):
        self.assertFileExists(a)
        self.assertFileExists(b)
        with open(a, 'r') as f:
            sa = f.read()
        with open(b, 'r') as f:
            sb = f.read()
        self.assertEqual(sa, sb)

    def assertFileNotExists(self, *args, **kws):
        msg = kws.get('msg', '')
        filename = os.path.join(*args)
        if os.path.exists(filename):
            self.fail('{} does exists although it should not. {}'.format(filename, msg))

    def assertFileExists(self, *args, **kws):
        msg = kws.get('msg', '')
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
            s = '''{}: filelists of
{}
and
{}
do not match.
In both:
{}
In first but not second:
{}
In second but not first:
{}
'''.format(failure_base, dir1, dir2,
           '  ' + ('\n  '.join(f for f in (files_dir1 & files_dir2)) or '(None)'),
           '  ' + ('\n  '.join(f for f in (files_dir1 - files_dir2)) or '(None)'),
           '  ' + ('\n  '.join(f for f in (files_dir2 - files_dir1)) or '(None)'),
          )
            self.fail(s)

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

