#!/usr/bin/env python3

import sys
sys.path.append('..')

import os
from os.path import join as J
import unittest
import logging

from test.utils import *
from harmony.working_directory import WorkingDirectory
from harmony.ruleset import Ruleset

logger = logging.getLogger(__name__)

class TestWorkingDirectory(TestCase):

    def make_mess(self, d):
        """
        Creates a mess of symlinked files and directories in d
        """
        real_filenames = set()

        echo('xxx', d, 'xxx.txt')
        real_filenames.add('xxx.txt')

        foobar = J(d, 'foo', 'bar')
        yyy_txt = J(foobar, 'yyy.txt')

        mkdir(foobar)
        echo('yyy', yyy_txt)
        real_filenames.add(J('foo', 'bar', 'yyy.txt'))

        os.symlink(foobar,  J(d, 'dir_shortcut'))
        os.symlink(yyy_txt, J(d, 'file_shortcut'))

        symlinks = {
            'file_shortcut': 'foo/bar/yyy.txt',
            'dir_shortcut/yyy.txt': 'foo/bar/yyy.txt',
        }

        return real_filenames, symlinks


    def ruleset_all(self, d):
        return Ruleset(d)

    def test_get_filenames_normalized(self):
        with TempDir() as d:
            real_filenames, _ = self.make_mess(d)
            wd = WorkingDirectory(d, self.ruleset_all(d))

            filenames = wd.get_filenames()
            self.assertEqual(set(real_filenames), set(filenames))

    def test_contains_normalized(self):
        with TempDir() as d:
            real_filenames, symlinks = self.make_mess(d)
            wd = WorkingDirectory(d, self.ruleset_all(d))

            for fn in real_filenames:
                self.assertTrue(fn in wd)

            # Note: WorkingDirectory.__contains__ is inconsistent with
            # WorkingDirectory.get_filenames in the sense that __contains__
            # also "shows" symlinks, so it might report more existing files
            for fn in symlinks:
                self.assertTrue(fn in wd)

    def test_generate_file_state_normalized(self):
        """
        generate_file_state() applied to real paths should retain the real paths
        in the returned FileState.

        generate_file_state() applied to symlinks should return a FileState
        with the real path instead of the symlink path.
        """

        with TempDir() as d:
            real_filenames, symlinks = self.make_mess(d)
            wd = WorkingDirectory(d, self.ruleset_all(d))

            for fn in real_filenames:
                state = wd.generate_file_state(fn)
                self.assertEqual(state.path, fn)

            for fn, real_fn in symlinks.items():
                state = wd.generate_file_state(fn)
                self.assertEqual(state.path, real_fn)


if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, format = '{levelname:7s} {module:15s}:{funcName:15s} | {message:s}', style = '{')
    unittest.main()

#  vim: set ts=4 sw=4 tw=79 expandtab :


