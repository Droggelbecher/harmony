
import logging

logger = logging.getLogger(__name__)

import yaml
import pathlib

# TODO: Merge this with harmony_component.py

def read(filename):
    filename = str(filename)
    r = None
    with open(filename, 'r') as f:
        s = f.read()
        r = yaml.safe_load(s)
    return r

def write(d, filename):
    filename = str(filename)
    with open(filename, 'w') as f:
        logger.debug('writing: {}'.format(filename))
        yaml.safe_dump(d, f)

def dump(d):
    return yaml.safe_dump(d)

# Note: The below would work for auto-converting paths to str's,
# but would require yaml.dump() instead of yaml.safe_dump() which
# would use tags (which I try to avoid for future parsability w/
# different libraries/languages)
#def represent_path(dumper, data):
#    return dumper.represent_str(str(data))
#yaml.add_representer(pathlib.Path, represent_path)
#yaml.add_representer(pathlib.PosixPath, represent_path)

