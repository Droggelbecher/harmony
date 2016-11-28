#!/usr/bin/env python

import sys
sys.path.append('../..')

import os
import unittest
import logging

from testutils import *
from harmony.clock import Clock

class TestClock(TestCase):

    def test_advance1_simple_from_empty(self):
        clock = Clock(a = 2, c = 1)
        clock.advance1(Clock(b = 1))
        self.assertEqual(clock, Clock(a = 2, b = 1, c = 1))

    def test_advance1_simple_from_empty_jump(self):
        clock = Clock(a = 2, c = 1)
        clock.advance1(Clock(b = 10))
        self.assertEqual(clock, Clock(a = 2, b = 10, c = 1))

    def test_advance1_multi_raises(self):
        clock = Clock(a = 2, c = 1)
        a = Clock(b = 1, c = 2)
        self.assertRaises(ValueError, clock.advance1, a)

    def test_advance1_backwards_raises(self):
        clock = Clock(a = 2, c = 1)
        a = Clock(a = 1)
        self.assertRaises(ValueError, clock.advance1, a)

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, format = '{levelname:7s} {module:15s}:{funcName:15s} | {message:s}', style = '{')
    unittest.main()
