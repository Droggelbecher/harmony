#!/usr/bin/env python

import sys
sys.path.append('../..')

import os
import unittest
import logging

from testutils import *
from harmony.repository import Repository


class TestRepository(unittest.TestCase):

    def test_init_creates_harmony_dir(self):
        with TempDir() as tmpdir:
            Repository.init(tmpdir)
            self.assertTrue(os.path.isdir(os.path.join(tmpdir, Repository.HARMONY_SUBDIR)))

    def test_init_fails_with_existing_harmony_dir(self):
        with TempDir() as tmpdir:
            os.mkdir(os.path.join(tmpdir, Repository.HARMONY_SUBDIR))
            self.assertRaises(FileExistsError, Repository.init, tmpdir)

    def test_find_finds_after_init(self):
        with TempDir() as tmpdir:
            Repository.init(tmpdir)
            mkdir(tmpdir, 'foo', 'bar')
            r = Repository.find(os.path.join(tmpdir, 'foo', 'bar'))
            self.assertIsNotNone(r)
            self.assertEqual(r.harmony_directory, os.path.join(tmpdir, '.harmony'))

    def test_load_works_after_init(self):
        with TempDir() as tmpdir:
            r0 = Repository.init(tmpdir)
            r = Repository.load(r0.harmony_directory)
            self.assertIsNotNone(r)
            self.assertEqual(r.harmony_directory, os.path.join(tmpdir, '.harmony'))


    def test_clone_empty(self):
        with TempDir() as tmpdir1, TempDir() as tmpdir2:
            r1 = Repository.init(tmpdir1)
            r2 = Repository.clone(tmpdir2, tmpdir1)

    #def test_clone_copies_certain_files(self):
        # TODO

    #def test_commit_creates_new_head(self):
        # TODO

    #def test_commit_without_changes_does_nothing(self):


    #def test_pull_state_gets_all_commits(self):

    #def test_pull_state_sets_remote_heads(self):

    #def test_pull_state_finds_conflicts(self):

    #def test_pull_state_auto_merges(self):

    #def test_pull_file_gets_file(self):

    #def test_pull_file_gets_newest_version(self):

    #def test_pull_file_prefers_local_protocol(self):






if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, format = '[{levelname:7s}] {message:s}', style = '{')
    unittest.main()

