
import unittest
from harmony.ruleset import Ruleset

class TestRuleset(unittest.TestCase):

    def test_match_path(self):
        f = Ruleset.match_path

        self.assertTrue(f('starstar/should/match/any.thing', '**'))

        self.assertFalse(f('singlestar/should/match/single/file.only', '*'))
        self.assertFalse(f('singlestar/should/match/single/file.only', '*.txt'))
        self.assertTrue(f('singlestar/should/match/single/file.only', '**/file.only'))

        self.assertTrue(f('singlestar/matches/single.file', 'singlestar/matches/*'))
        self.assertTrue(f('singlestar/matches/single.file', 'singlestar/matches/*.file'))
        self.assertFalse(f('singlestar/matches/single.file', 'singlestar/matches/*.txt'))
        self.assertFalse(f('singlestar/should/match/single/file.only', 'should'))
        self.assertTrue(f('singlestar/should/match/single/file.only', '**/should/**'))
        self.assertTrue(f('singlestar/should/match/single/file.only', '**/should/**/*.only'))


    def test_match_directory(self):
        f = Ruleset.match_directory

        self.assertTrue(f('foo/bar/baz/bang.txt', 'foo'))
        self.assertTrue(f('foo/bar/baz/bang.txt', 'bar'))
        self.assertTrue(f('foo/bar/baz/bang.txt', 'baz'))
        self.assertFalse(f('foo/bar/baz/bang.txt', 'bang.txt'))

        self.assertTrue(f('foo/bar/baz/bang.txt', 'f*'))
        self.assertTrue(f('foo/bar/baz/bang.txt', 'b*'))
        self.assertFalse(f('foo/bar/baz/bang.txt', '*x*'))

