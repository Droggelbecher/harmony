
import logging
from datetime import datetime
from pathlib import Path

from harmony import util

logger = logging.getLogger(__name__)

def test_datetime_to_iso():
    d = datetime(2018, 7, 22, 13, 54, 42)
    assert util.datetime_to_iso(d) == '2018-07-22T13:54:42.000000'

def test_iso_to_datetime():
    iso = '2018-07-22T13:54:42.000000'
    d = datetime(2018, 7, 22, 13, 54, 42)
    assert util.iso_to_datetime(iso) == d

def test_has_suffix():
    a = Path('foo', 'bar', 'bang', 'baz')
    assert util.has_suffix(a, Path('baz'))
    assert util.has_suffix(a, Path('bang', 'baz'))
    assert util.has_suffix(a, a)

    assert not util.has_suffix(a, Path('bang'))
    assert not util.has_suffix(a, Path('foo'))
    assert not util.has_suffix(a, Path('frobnizer'))


