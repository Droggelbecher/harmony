#!/usr/bin/env python3

import sys

import os
import logging
from pathlib import Path

from tests.utils import *
from harmony.working_directory import WorkingDirectory
from harmony.ruleset import Ruleset

logger = logging.getLogger(__name__)

def make_mess(d):
    """
    Creates a mess of symlinked files and directories in d
    """
    real_filenames = set()

    (d / 'xxx.txt').write_text('xxx')
    real_filenames.add(Path('xxx.txt'))

    foobar = d / 'foo' / 'bar'
    yyy_txt = foobar / 'yyy.txt'

    foobar.mkdir(parents = True)
    yyy_txt.write_text('yyy')
    real_filenames.add(Path('foo') / 'bar' / 'yyy.txt')

    (d / 'dir_shortcut').symlink_to(foobar)
    (d / 'file_shortcut').symlink_to(yyy_txt)

    symlinks = {
        'file_shortcut': 'foo/bar/yyy.txt',
        'dir_shortcut/yyy.txt': 'foo/bar/yyy.txt',
    }

    return real_filenames, symlinks


def ruleset_all(d):
    return Ruleset(d)

def test_get_filenames_normalized():
    with TempDir() as d:
        real_filenames, _ = make_mess(d)
        wd = WorkingDirectory(d, ruleset_all(d))

        filenames = wd.get_filenames()
        assert set(real_filenames) == set(filenames)

def test_contains_normalized():
    with TempDir() as d:
        real_filenames, symlinks = make_mess(d)
        wd = WorkingDirectory(d, ruleset_all(d))

        for fn in real_filenames:
	        assert fn in wd

        # Note: WorkingDirectory.__contains__ is inconsistent with
        # WorkingDirectory.get_filenames in the sense that __contains__
        # also "shows" symlinks, so it might report more existing files
        for fn in symlinks:
	        assert fn in wd

def test_generate_file_state_normalized():
    """
    generate_file_state() applied to real paths should retain the real paths
    in the returned FileState.

    generate_file_state() applied to symlinks should return a FileState
    with the real path instead of the symlink path.
    """

    with TempDir() as d:
        real_filenames, symlinks = make_mess(d)
        wd = WorkingDirectory(d, ruleset_all(d))

        for fn in real_filenames:
            state = wd.generate_file_state(fn)
            assert Path(state.path) == Path(fn)

        for fn, real_fn in symlinks.items():
            state = wd.generate_file_state(fn)
            assert Path(state.path) == Path(real_fn)


#  vim: set ts=4 sw=4 tw=79 expandtab :


