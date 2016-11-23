
# Not available in py3
#import dateutil

# This is not exactly ISO 8601, but close.
# Unfortunately datetime can't parse its own .isoformat() output
# (d'oh!)
# TODO: iirc there is a function for parsing ISO8601 correctly somewhere in
# datetime or so.
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

def datetime_to_iso(d):
    #return d.isoformat()
    return d.strftime(DATETIME_FORMAT)

def iso_to_datetime(s):
    #return dateutil.parser.parse(s)
    return d.strptime(s, DATETIME_FORMAT)


