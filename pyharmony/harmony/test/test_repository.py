#!/usr/bin/env python

import sys
sys.path.append('../..')

import os
from os.path import join as J
import unittest
import logging

from testutils import *
from harmony.repository import Repository


class TestRepository(TestCase):

    def test_init_creates_harmony_dir(self):
        with TempDir() as tmpdir:
            Repository.init(tmpdir)
            self.assertTrue(os.path.isdir(J(tmpdir, Repository.HARMONY_SUBDIR)))

    def test_init_fails_with_existing_harmony_dir(self):
        with TempDir() as tmpdir:
            os.mkdir(J(tmpdir, Repository.HARMONY_SUBDIR))
            self.assertRaises(FileExistsError, Repository.init, tmpdir)

    def test_find_finds_after_init(self):
        with TempDir() as tmpdir:
            Repository.init(tmpdir)
            mkdir(tmpdir, 'foo', 'bar')
            r = Repository.find(J(tmpdir, 'foo', 'bar'))
            self.assertIsNotNone(r)
            self.assertEqual(r.harmony_directory, J(tmpdir, '.harmony'))

    def test_load_works_after_init(self):
        with TempDir() as tmpdir:
            r0 = Repository.init(tmpdir)
            r = Repository.load(r0.harmony_directory)
            self.assertIsNotNone(r)
            self.assertEqual(r.harmony_directory, J(tmpdir, '.harmony'))


    def test_clone_empty(self):
        with TempDir() as tmpdir1, TempDir() as tmpdir2:
            r1 = Repository.init(tmpdir1)
            r2 = Repository.clone(tmpdir2, tmpdir1)
            self.assertFileExists(tmpdir2, '.harmony', 'config', msg="config file after clone")

    def test_clone_copies_certain_files(self):
        with TempDir() as tmpdir1, TempDir() as tmpdir2:
            r1 = Repository.init(tmpdir1)
            echo('hallo', tmpdir1, 'hallo.txt')
            r1.commit()
            r2 = Repository.clone(tmpdir2, tmpdir1)
            self.assertFileExists(tmpdir2, '.harmony', 'config', msg="config file after clone")
            self.assertDirectoriesEqual(
                J(tmpdir1, '.harmony', 'commits'),
                J(tmpdir2, '.harmony', 'commits')
                )

    def test_commit_creates_new_head(self):
        with TempDir() as tmpdir1:
            r1 = Repository.init(tmpdir1)
            echo('hallo', tmpdir1, 'hallo.txt')
            r1.commit()
            head_path = J(tmpdir1, '.harmony', 'HEAD')
            self.assertFileExists(head_path)
            with open(head_path, 'r') as f:
                self.assertFileExists(tmpdir1, '.harmony', 'commits', f.read().strip())

    def test_commit_without_changes_does_nothing(self):
        with TempDir() as tmpdir1:
            r1 = Repository.init(tmpdir1)
            echo('hallo', tmpdir1, 'hallo.txt')
            r1.commit()
            commits = os.listdir(J(tmpdir1, '.harmony', 'commits'))
            self.assertEqual(1, len(commits))

            r1.commit()
            commits2 = os.listdir(J(tmpdir1, '.harmony', 'commits'))
            self.assertCountEqual(commits, commits2)

    def test_commit_with_changes_does_something(self):
        with TempDir() as tmpdir1:
            r1 = Repository.init(tmpdir1)
            echo('hallo', J(tmpdir1, 'hallo.txt'))
            r1.commit()
            commits = os.listdir(J(tmpdir1, '.harmony', 'commits'))
            self.assertEqual(1, len(commits))

            echo('hallo, welt', J(tmpdir1, 'hallo.txt'))
            r1.commit()
            commits2 = os.listdir(J(tmpdir1, '.harmony', 'commits'))
            self.assertEqual(2, len(commits2))

    def test_pull_state_gets_all_commits(self):
        with TempDir() as tmpdir1, TempDir() as tmpdir2:

            # Create R1 with a number of commits
            #

            r1 = Repository.init(tmpdir1)

            echo('hallo', J(tmpdir1, 'hallo.txt'))
            r1.commit()

            echo('hello', J(tmpdir1, 'hello.txt'))
            r1.commit()

            echo('Hallo, Welt', J(tmpdir1, 'hallo.txt'))
            r1.commit()

            echo('Hallo, Welt!', J(tmpdir1, 'hallo.txt'))
            echo('Hello, World!', J(tmpdir1, 'hello.txt'))
            r1.commit()

            # Create R2 and pull state from R1
            #

            r2 = Repository.init(tmpdir2)
            r2.pull_state(tmpdir1)

            self.assertDirectoriesEqual(
                    J(tmpdir1, '.harmony', 'commits'),
                    J(tmpdir2, '.harmony', 'commits')
                    )

            self.assertFileContentsEqual(
                    J(tmpdir1, '.harmony', 'HEAD'),
                    J(tmpdir2, '.harmony', 'remote-heads', r1.get_id())
                    )

    def test_pull_state_finds_conflicts(self):
        with TempDir() as tmpdir1, TempDir() as tmpdir2:

            # Create R1 with a number of commits
            #

            r1 = Repository.init(tmpdir1)

            echo('hallo', J(tmpdir1, 'hallo.txt'))
            r1.commit()

            r2 = Repository.clone(tmpdir2, tmpdir1)

            echo('hello', J(tmpdir1, 'hello.txt'))
            r1.commit()

            echo('Hallo, Welt', J(tmpdir1, 'hallo.txt'))
            r1.commit()

            echo('Hallo, Welt!', J(tmpdir1, 'hallo.txt'))
            echo('Hello, World!', J(tmpdir1, 'hello.txt'))
            r1.commit()


            echo("Guten Tag, Welt!", J(tmpdir2, 'hallo.txt'))
            echo("Hello, World!!", J(tmpdir2, 'hello.txt'))
            r2.commit()

            conflicts = r2.pull_state(tmpdir1)
            self.assertEqual(2, len(conflicts))

            heads = r2.history.get_head_ids()
            self.assertEqual(2, len(heads))

    def test_pull_state_auto_merges(self):
        with TempDir() as tmpdir1, TempDir() as tmpdir2:

            # Create R1 with a number of commits
            #

            # --- R1

            r1 = Repository.init(tmpdir1)

            echo('hallo', J(tmpdir1, 'hallo.txt'))
            r1.commit()


            r2 = Repository.clone(tmpdir2, tmpdir1)

            echo('hello', J(tmpdir1, 'hello.txt'))
            r1.commit()

            echo('Hallo, Welt', J(tmpdir1, 'hallo.txt'))
            r1.commit()

            echo('Hallo, Welt!', J(tmpdir1, 'hallo.txt'))
            echo('Hello, World!', J(tmpdir1, 'hello.txt'))
            r1.commit()

            # --- R2

            # Same content as on R!
            echo('Hello, World!', J(tmpdir2, 'hello.txt'))
            r2.commit()

            conflicts = r2.pull_state(tmpdir1)
            self.assertEqual(0, len(conflicts))

            r2.history.format_log()

            heads = r2.history.get_head_ids()
            self.assertEqual(1, len(heads))



    #def test_pull_file_gets_file(self):

    #def test_pull_file_gets_newest_version(self):

    #def test_pull_file_prefers_local_protocol(self):






if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, format = '[{levelname:7s}] {message:s}', style = '{')
    unittest.main()

