#!/usr/bin/env python

import sys
import logging

from harmony.ruleset import Ruleset

def test_match_path():
    f = Ruleset.match_path

    assert f('starstar/should/match/any.thing', '**')

    assert not f('singlestar/should/match/single/file.only', '*')
    assert not f('singlestar/should/match/single/file.only', '*.txt')
    assert f('singlestar/should/match/single/file.only', '**/file.only')

    assert f('singlestar/matches/single.file', 'singlestar/matches/*')
    assert f('singlestar/matches/single.file', 'singlestar/matches/*.file')
    assert not f('singlestar/matches/single.file', 'singlestar/matches/*.txt')
    assert not f('singlestar/should/match/single/file.only', 'should')
    assert f('singlestar/should/match/single/file.only', '**/should/**')
    assert f('singlestar/should/match/single/file.only', '**/should/**/*.only')


def test_match_directory():
    f = Ruleset.match_directory

    assert f('foo/bar/baz/bang.txt', 'foo')
    assert f('foo/bar/baz/bang.txt', 'bar')
    assert f('foo/bar/baz/bang.txt', 'baz')
    assert not f('foo/bar/baz/bang.txt', 'bang.txt')

    assert f('foo/bar/baz/bang.txt', 'f*')
    assert f('foo/bar/baz/bang.txt', 'b*')
    assert not f('foo/bar/baz/bang.txt', '*x*')

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, format = '{levelname:7s} {module:15s}:{funcName:15s} | {message:s}', style = '{')
    unittest.main()
