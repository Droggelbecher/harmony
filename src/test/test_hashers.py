#!/usr/bin/env python3

import sys
sys.path.append('..')

import os
import pathlib
import unittest
import logging
from io import BytesIO

from testutils import *
from harmony.hashers import get_hasher


logger = logging.getLogger(__name__)


class TestHashers(TestCase):

    def test_throw_on_incorrect_hasher_name(self):
        with self.assertRaises(ValueError) as context:
            get_hasher('someFunkyNonExistentHasher')

    def test_has_sha1(self):
        hasher = get_hasher('sha1')
        self.assertIsNotNone(hasher)

    def test_sha1_of_empty(self):
        empty = BytesIO()
        hasher = get_hasher('sha1')

        digest = hasher(empty)
        self.assertEqual(digest, 'sha1:da39a3ee5e6b4b0d3255bfef95601890afd80709')

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, format = '{levelname:7s} {module:15s}:{funcName:15s} | {message:s}', style = '{')
    unittest.main()

#  vim: set ts=4 sw=4 tw=79 expandtab :

