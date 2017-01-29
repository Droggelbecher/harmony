#!/usr/bin/env python3

import sys

import os
import pytest
import logging
from pathlib import Path

from tests.utils import *
from harmony.repository import Repository

LOCATION_STATE_DIR = 'location_states'

logger = logging.getLogger(__name__)


"""
Tests the high-level functions of the Repository class.
This actually tests almost end-to-end (starting just below where a command
line interface would be), so its more of a component test than a unit test.

These tests naturally consider a lot of file-system related questions such
as whether a file is correctly transferred etc.. and thus make excessive use
of file system related functions/tools such as TempDir(), assertFileExists(),
etc... (see test.utils for most of the implementations)
"""

d_harmony = Repository.HARMONY_SUBDIR

@pytest.fixture(autouse = True)
def setup():
    logging.basicConfig(level = logging.DEBUG, format = '{levelname:7s} {module:15s}:{funcName:15s} | {message:s}', style = '{')

def test_init_creates_harmony_dir():
    with TempDir() as d:
        Repository.init(d)
        assert (d / d_harmony).is_dir()

def test_init_fails_with_existing_harmony_dir():
    with TempDir() as d:
        (d / d_harmony).mkdir()
        with pytest.raises(FileExistsError):
            Repository.init(d)

def test_find_repository_from_subdir():
    with TempDir() as d:
        Repository.init(d)

        foobar = d / 'foo' / 'bar'
        foobar.mkdir(parents = True)
        r = Repository.find(foobar)
        assert r is not None
        assert Path(r.harmony_directory) == (d / d_harmony)

def test_load_repository_from_harmony_dir():
    with TempDir() as d:
        r0 = Repository.init(d)
        r = Repository.load(r0.harmony_directory)
        assert r is not None
        assert Path(r.harmony_directory) == (d / d_harmony)


def test_pull_state_copies_certain_files():
    with TempDir() as d1, TempDir() as d2:
        r1 = Repository.init(d1)
        (d1 / 'hallo.txt').write_text('hallo')
        r1.commit()

        r2 = Repository.init(d2)

        logger.debug('pulling {} -> {}'.format(d1, d2))
        r2.pull_state(d1)

        # r2 should now contain the location state of r1,
        # but not yet one of its own.
        assert directories_equal(
            d1 / d_harmony / LOCATION_STATE_DIR,
            d2 / d_harmony / LOCATION_STATE_DIR
            )


def test_clone_empty():
    with TempDir() as d1, TempDir() as d2:
        r1 = Repository.init(d1)
        r2 = Repository.clone(d2, d1)
        assert (d2 / d_harmony / 'config').is_file()

def test_clone_copies_certain_files():
    with TempDir() as d1, TempDir() as d2:
        r1 = Repository.init(d1)
        (d1 / 'hallo.txt').write_text('hallo')
        r1.commit()

        r2 = Repository.clone(d2, d1)
        assert (d2 / d_harmony / 'config').is_file()

        assert directories_equal(
            d1 / d_harmony / LOCATION_STATE_DIR,
            d2 / d_harmony / LOCATION_STATE_DIR
            )

def test_one_location_state_iff_there_have_been_local_commits_only():
    with TempDir() as d1:
        r1 = Repository.init(d1)
        location_states = tuple((d1 / d_harmony / LOCATION_STATE_DIR).iterdir())
        assert len(location_states) == 0

        (d1 / 'hallo.txt').write_text('hallo')
        r1.commit()
        location_states = tuple((d1 / d_harmony / LOCATION_STATE_DIR).iterdir())
        assert len(location_states) == 1

        (d1 / 'hallo.txt').write_text('hallo, welt')
        r1.commit()
        location_states = tuple((d1 / d_harmony / LOCATION_STATE_DIR).iterdir())
        assert len(location_states) == 1

def test_pull_state_finds_conflict():
    with TempDir() as d1, TempDir() as d2:

        r1 = Repository.init(d1)
        (d1 / 'hallo.txt').write_text('hallo')
        r1.commit()

        # clock @R1 { r1 = 1 }

        r2 = Repository.clone(d2, d1)

        # clock @R2 { r1 = 1, r2 = 0 }

        (d1 / 'hallo.txt').write_text('hallo-r1')
        r1.commit()

        # clock @R1 { r1 = 2 }

        # This change (hallo->hallo-r2) is not actually a merge,
        # but since the file wasnt loaded before in R2, it should have
        # raised a confirmation to the user.
        (d2 / 'hallo.txt').write_text('hallo-r2')
        r2.commit()

        # clock @R2 { r1 = 2, r2 = 1 }

        conflicts = r2.pull_state(d1)
        assert len(conflicts) == 1

def test_pull_state_automerge_same_content_clock_value():
    # White-box test
    with TempDir() as A, TempDir() as B:
        rA = Repository.init(A)
        rB = Repository.clone(B, A)

        logger.debug('A.id={}'.format(rA.id))
        logger.debug('B.id={}'.format(rB.id))

        (A / 'hello.txt').write_text('Hello, World!')
        rA.commit()
        state_a = rA.repository_state['hello.txt']

        (B / 'hello.txt').write_text('Hello, World!')
        rB.commit()
        state_b = rB.repository_state['hello.txt']

        assert not state_a.clock.comparable(state_b.clock), 'clk A={} clk B={}'.format(state_a.clock, state_b.clock)


        rB.pull_state(A)

        # Auto merge should happen and identify the same contents,
        # resulting in a new commit in B with a merged clock value
        state_b_new = rB.repository_state['hello.txt']
        assert state_b_new.clock > state_b.clock, 'clk Bnew={} clk B={}'.format(state_b_new.clock, state_b.clock)
        assert state_b_new.clock > state_a.clock, 'clk Bnew={} clk A={}'.format(state_b_new.clock, state_a.clock)


def test_pull_state_finds_conflicts():
    with TempDir() as d1, TempDir() as d2:

        # Create R1 with a number of commits
        #

        # -- 1 --
        r1 = Repository.init(d1)
        logger.debug('-- Creating stuff in R1')
        (d1 / 'hallo.txt').write_text('hallo')
        r1.commit()

        logger.debug('-- Cloning')
        r2 = Repository.clone(d2, d1)

        # -- 1 --
        logger.debug('-- Changing stuff in R1')
        (d1 / 'hello.txt').write_text('hello')
        r1.commit()

        (d1 / 'hallo.txt').write_text('Hallo, Welt')
        r1.commit()

        (d1 / 'hallo.txt').write_text('Hallo, Welt!')
        (d1 / 'hello.txt').write_text('Hello, World!')
        r1.commit()

        # -- 2 --
        logger.debug('-- Changing stuff in R2')
        (d2 / 'hallo.txt').write_text('Guten Tag, Welt!')
        (d2 / 'hello.txt').write_text('Hello, World!!')
        r2.commit()

        logger.debug('-- Pull R1 -> R2')

        conflicts = r2.pull_state(d1)
        assert len(conflicts) == 2


def test_pull_state_conflicts_on_adding():
    with TempDir() as A, TempDir() as B:

        rA = Repository.init(A)
        rB = Repository.clone(B, A)

        (A / 'x.txt').write_text('Added in A')
        rA.commit()

        (B / 'x.txt').write_text('Added in B')
        rB.commit()

        conflicts = rB.pull_state(A)
        assert len(conflicts) == 1


def test_pull_state_auto_merges_equal_content():
    with TempDir() as d1, TempDir() as d2:

        # Create R1 with a number of commits
        #

        # --- R1

        r1 = Repository.init(d1)

        (d1 / 'hallo.txt').write_text('hallo')
        r1.commit()


        r2 = Repository.clone(d2, d1)

        (d1 / 'hello.txt').write_text('hello')
        r1.commit()

        (d1 / 'hallo.txt').write_text('Hallo, Wolt')
        r1.commit()

        (d1 / 'hallo.txt').write_text('Hallo, Welt!')
        (d1 / 'hello.txt').write_text('Hello, World!')
        r1.commit()

        # --- R2

        # Same content as on R1
        (d2 / 'hello.txt').write_text('Hello, World!')
        r2.commit()

        conflicts = r2.pull_state(d1)
        assert len(conflicts) == 0


def test_pull_file_simple():

    with TempDir() as A, TempDir() as B:

        rA = Repository.init(A)
        rB = Repository.clone(B, A)

        (A / 'x.txt').write_text('Hello, World')
        rA.commit()

        conflicts = rB.pull_state(A)
        assert len(conflicts) == 0

        rB.pull_file('x.txt', A)
        assert (A / 'x.txt').read_bytes() == (B / 'x.txt').read_bytes()


def test_pull_state_autodetects_rename():

    with TempDir() as A, TempDir() as B:

        rA = Repository.init(A)
        rB = Repository.clone(B, A)

        (A / 'x.txt').write_text('Hello, World')
        rA.commit()

        conflicts = rB.pull_state(A)
        assert len(conflicts) == 0
        rB.pull_file('x.txt', A)

        assert (A / 'x.txt').read_bytes() == (B / 'x.txt').read_bytes()

        (A / 'x.txt').rename(A / 'y.txt')

        rA.commit()

        conflicts = rB.pull_state(A)

        assert len(conflicts) == 0
        assert not (A / 'x.txt').exists()
        assert not (B / 'x.txt').exists()
        assert (A / 'y.txt').read_bytes() == (B / 'y.txt').read_bytes()

def test_rename_does_nothing_for_unpulled():

    with TempDir() as A, TempDir() as B:

        rA = Repository.init(A)
        rB = Repository.clone(B, A)

        (A / 'x.txt').write_text('Hello, World')
        rA.commit()

        conflicts = rB.pull_state(A)
        assert len(conflicts) == 0

        assert not (B / 'x.txt').exists()

        (A / 'x.txt').rename(A / 'y.txt')
        rA.commit()

        conflicts = rB.pull_state(A)
        assert len(conflicts) == 0
        assert not (A / 'x.txt').exists()
        assert (A / 'y.txt').is_file()
        assert not (B / 'x.txt').exists()
        assert not (B / 'y.txt').exists()


def test_rename_updates_location_state():

    with TempDir() as A, TempDir() as B, TempDir() as C:

        rA = Repository.init(A)
        rB = Repository.clone(B, A)

        # A
        (A / 'x.txt').write_text('Hello, World')
        rA.commit()

        # B
        conflicts = rB.pull_state(A)
        rB.pull_file('x.txt', A)

        # A
        (A / 'x.txt').rename(A / 'y.txt')
        rA.commit()

        # B
        conflicts = rB.pull_state(A)
        change = rB.commit()
        assert not change

        # We established in the previous tests already that B
        # should now have auto-renamed x.txt to y.txt.
        # After that it shall automatically update its location state
        # (no additional "commit" necessary after pull_state),
        # and thus allow the file to be retrieved as y.txt in a third
        # repository C:

        # C
        rC = Repository.clone(C, B)
        rC.pull_file('y.txt', B)

        assert (A / 'y.txt').read_bytes() == (C / 'y.txt').read_bytes()


# TODO:
# - file deletion
# - multiple files with same contents
# - that also in the presence of moving/deletion


#def test_pull_file_gets_file():

#def test_pull_file_gets_newest_version():

#def test_pull_file_prefers_local_protocol():






if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, format = '{levelname:7s} {module:20s}:{funcName:15s} | {message:s}', style = '{')
    unittest.main()

#  vim: set ts=4 sw=4 tw=79 expandtab :
