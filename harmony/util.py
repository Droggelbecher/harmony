
from pathlib import Path

# Not available in py3
#import dateutil

# This is not exactly ISO 8601, but close.
# Unfortunately datetime can't parse its own .isoformat() output
# (d'oh!)
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

def datetime_to_iso(d):
    return d.strftime(DATETIME_FORMAT)

def iso_to_datetime(s):
    import datetime
    return datetime.datetime.strptime(s, DATETIME_FORMAT)

def shortened_id(id_):
    return id_[4:8]

def has_suffix(a: Path, b: Path) -> bool:
    """Return True iff a has path b as suffix"""
    return a.parts[-len(b.parts):] == b.parts

