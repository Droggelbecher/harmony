#!/usr/bin/env python

import sys
sys.path.append('../..')

import os
from os.path import join as J
import unittest
import logging

from testutils import *
from harmony.repository import Repository

LOCATION_STATE_DIR = 'location_states'

logger = logging.getLogger(__name__)


class TestRepository(TestCase):

    """
    Tests the high-level functions of the Repository class.
    This actually tests almost end-to-end (starting just below where a command
    line interface would be), so its more of a component test than a unit test.

    These tests naturally consider a lot of file-system related questions such
    as whether a file is correctly transferred etc.. and thus make excessive use
    of file system related functions/tools such as TempDir(), assertFileExists(),
    etc... (see testutils for most of the implementations)
    """

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
                J(tmpdir1, '.harmony', LOCATION_STATE_DIR),
                J(tmpdir2, '.harmony', LOCATION_STATE_DIR)
                )

    def test_one_location_state_iff_there_have_been_local_commits_only(self):
        with TempDir() as tmpdir1:
            r1 = Repository.init(tmpdir1)
            location_states = os.listdir(J(tmpdir1, '.harmony',
                                           LOCATION_STATE_DIR))
            self.assertEqual(0, len(location_states))

            echo('hallo', J(tmpdir1, 'hallo.txt'))
            r1.commit()
            location_states = os.listdir(J(tmpdir1, '.harmony',
                                           LOCATION_STATE_DIR))
            self.assertEqual(1, len(location_states))

            echo('hallo, welt', J(tmpdir1, 'hallo.txt'))
            r1.commit()
            location_states = os.listdir(J(tmpdir1, '.harmony',
                                           LOCATION_STATE_DIR))
            self.assertEqual(1, len(location_states))

    def test_pull_state_finds_conflict(self):
        with TempDir() as tmpdir1, TempDir() as tmpdir2:

            r1 = Repository.init(tmpdir1)
            echo('hallo', J(tmpdir1, 'hallo.txt'))
            r1.commit()

            # clock @R1 { r1 = 1 }

            r2 = Repository.clone(tmpdir2, tmpdir1)

            # clock @R2 { r1 = 1, r2 = 0 }

            echo('hallo-r1', J(tmpdir1, 'hallo.txt'))
            r1.commit()

            # clock @R1 { r1 = 2 }

            # This change (hallo->hallo-r2) is not actually a merge,
            # but since the file wasnt loaded before in R2, it should have
            # raised a confirmation to the user.
            echo('hallo-r2', J(tmpdir2, 'hallo.txt'))
            r2.commit()

            # clock @R2 { r1 = 1, r2 = 1 }

            conflicts = r2.pull_state(tmpdir1)
            self.assertEqual(1, len(conflicts))


    def test_pull_state_finds_conflicts(self):
        with TempDir() as tmpdir1, TempDir() as tmpdir2:

            # Create R1 with a number of commits
            #

            r1 = Repository.init(tmpdir1)

            logger.debug('-- Creating stuff in R1')

            # -- 1 --
            echo('hallo', J(tmpdir1, 'hallo.txt'))
            r1.commit()

            logger.debug('-- Cloning')

            r2 = Repository.clone(tmpdir2, tmpdir1)

            logger.debug('-- Changing stuff in R1')

            # -- 1 --
            echo('hello', J(tmpdir1, 'hello.txt'))
            r1.commit()

            # -- 1 --
            echo('Hallo, Welt', J(tmpdir1, 'hallo.txt'))
            r1.commit()

            # -- 1 --
            echo('Hallo, Welt!', J(tmpdir1, 'hallo.txt'))
            echo('Hello, World!', J(tmpdir1, 'hello.txt'))
            r1.commit()

            logger.debug('-- Changing stuff in R2')

            # -- 2 --
            echo("Guten Tag, Welt!", J(tmpdir2, 'hallo.txt'))
            echo("Hello, World!!", J(tmpdir2, 'hello.txt'))
            r2.commit()

            logger.debug('-- Pull R1 -> R2')

            conflicts = r2.pull_state(tmpdir1)
            self.assertEqual(2, len(conflicts))


    def test_pull_state_conflicts_on_adding(self):
        with TempDir() as A, TempDir() as B:

            rA = Repository.init(A)
            rB = Repository.clone(B, A)

            echo('Added in A', J(A, 'x.txt'))
            rA.commit()

            echo('Added in B', J(B, 'x.txt'))
            rB.commit()

            conflicts = rB.pull_state(A)
            self.assertEqual(1, len(conflicts))



    def test_pull_state_auto_merges_equal_content(self):
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

            # Same content as on R1
            echo('Hello, World!', J(tmpdir2, 'hello.txt'))
            r2.commit()

            conflicts = r2.pull_state(tmpdir1)
            self.assertEqual(0, len(conflicts))


    def test_pull_file_simple(self):

        with TempDir() as A, TempDir() as B:

            rA = Repository.init(A)
            rB = Repository.clone(B, A)

            echo('Hello, World', J(A, 'x.txt'))
            rA.commit()

            conflicts = rB.pull_state(A)
            self.assertEqual(0, len(conflicts))

            rB.pull_file('x.txt', A)
            self.assertFilesEqual(J(A, 'x.txt'), J(B, 'x.txt'))



    def test_pull_state_autodetects_rename(self):

        with TempDir() as A, TempDir() as B:

            rA = Repository.init(A)
            rB = Repository.clone(B, A)

            echo('Hello, World', J(A, 'x.txt'))
            rA.commit()

            conflicts = rB.pull_state(A)
            self.assertEqual(0, len(conflicts))
            rB.pull_file('x.txt', A)
            self.assertFilesEqual(J(A, 'x.txt'), J(B, 'x.txt'))

            mv(J(A, 'x.txt'), J(A, 'y.txt'))
            rA.commit()

            conflicts = rB.pull_state(A)
            self.assertEqual(0, len(conflicts))
            self.assertFileNotExists(J(A, 'x.txt'))
            self.assertFileNotExists(J(B, 'x.txt'))
            self.assertFilesEqual(J(A, 'y.txt'), J(B, 'y.txt'))

    def test_rename_does_nothing_for_unpulled(self):

        with TempDir() as A, TempDir() as B:

            rA = Repository.init(A)
            rB = Repository.clone(B, A)

            echo('Hello, World', J(A, 'x.txt'))
            rA.commit()

            conflicts = rB.pull_state(A)
            self.assertEqual(0, len(conflicts))

            self.assertFileNotExists(J(B, 'x.txt'))

            mv(J(A, 'x.txt'), J(A, 'y.txt'))
            rA.commit()

            conflicts = rB.pull_state(A)
            self.assertEqual(0, len(conflicts))
            self.assertFileNotExists(J(A, 'x.txt'))
            self.assertFileExists(J(A, 'y.txt'))
            self.assertFileNotExists(J(B, 'x.txt'))
            self.assertFileNotExists(J(B, 'y.txt'))

    def test_rename_updates_location_state(self):

        with TempDir() as A, TempDir() as B, TempDir() as C:

            rA = Repository.init(A)
            rB = Repository.clone(B, A)

            # A
            echo('Hello, World', J(A, 'x.txt'))
            rA.commit()

            # B
            conflicts = rB.pull_state(A)
            rB.pull_file('x.txt', A)

            # A
            mv(J(A, 'x.txt'), J(A, 'y.txt'))
            rA.commit()

            # B
            conflicts = rB.pull_state(A)
            change = rB.commit()
            self.assertFalse(change)

            # We established in the previous tests already that B
            # should now have auto-renamed x.txt to y.txt.
            # After that it shall automatically update its location state
            # (no additional "commit" necessary after pull_state),
            # and thus allow the file to be retrieved as y.txt in a third
            # repository C:

            # C
            rC = Repository.clone(C, B)
            rC.pull_file('y.txt', B)
            self.assertFilesEqual(J(A, 'y.txt'), J(C, 'y.txt'))


    # TODO:
    # - file deletion
    # - multiple files with same contents
    # - that also in the presence of moving/deletion


    #def test_pull_file_gets_file(self):

    #def test_pull_file_gets_newest_version(self):

    #def test_pull_file_prefers_local_protocol(self):






if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, format = '{levelname:7s} {module:15s}:{funcName:15s} | {message:s}', style = '{')
    unittest.main()

#  vim: set ts=4 sw=4 tw=79 expandtab :
