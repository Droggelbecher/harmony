#!/usr/bin/env python

import sys
sys.path.append('../..')

import os
import unittest
import logging

from testutils import *
from harmony.file_state import FileState

class TestFileState(TestCase):

    def test_get_heads_empty(self):
        states = ()
        self.assertEqual(set(), FileState.get_heads(states))

    def test_get_heads_one_item(self):
        states = [
            FileState(clock = { 'a': 1, 'b': 4, 'd': 0 })
        ]
        self.assertEqual(set(states), FileState.get_heads(states))

    def test_get_heads_default_state(self):
        expected_head = FileState(clock = { 'a': 2, 'b': 13, 'e': 9 })
        states = [
            FileState(),
            expected_head
        ]
        self.assertEqual(set([expected_head]), FileState.get_heads(set(states)))

    def test_get_heads_chain(self):
        expected_head = FileState(clock = { 'a': 2, 'b': 13, 'e': 9 })
        states = [
            FileState(clock = { 'a': 1, 'b': 4, 'd': 0 }),
            FileState(clock = { 'a': 1, 'b': 5, 'd': 0 }),
            FileState(clock = { 'a': 2, 'b': 10, 'd': 0, 'e': 8 }),
            FileState(clock = { 'a': 1, 'b': 4 }),
            FileState(clock = { 'a': 2, 'b': 12, 'd': 0, 'e': 8 }),
            expected_head
        ]

        # the set() within get_heads is not necessary but illustrates that we
        # can remove order
        self.assertEqual(set([expected_head]), FileState.get_heads(set(states)))

    # TODO: test get_heads in a non-degenarate DAG case

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, format = '[{levelname:7s}] {message:s}', style = '{')
    unittest.main()
