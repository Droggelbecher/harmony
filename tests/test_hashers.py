#!/usr/bin/env python3

import sys

import os
from pathlib import Path
import logging
from io import BytesIO
from pytest import raises

from tests.utils import *
from harmony.hashers import get_hasher


logger = logging.getLogger(__name__)

def test_throw_on_incorrect_hasher_name():
    with raises(ValueError):
        get_hasher('someFunkyNonExistentHasher')

def test_has_sha1():
    hasher = get_hasher('sha1')
    assert hasher is not None

def test_sha1_of_empty():
    empty = BytesIO()
    hasher = get_hasher('sha1')

    digest = hasher(empty)
    assert digest == 'sha1:da39a3ee5e6b4b0d3255bfef95601890afd80709'


#  vim: set ts=4 sw=4 tw=79 expandtab :

