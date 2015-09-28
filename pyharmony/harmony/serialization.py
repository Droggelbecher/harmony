
import logging

try:
    import yaml

except ImportError:

    logging.warn("""
    PYTHON-YAML NOT FOUND.
    HARMONY IS NOT OPERATIONAL FOR PRODUCTION WITHOUT PYTHON-YAML.
    IT WILL HOWEVER CONTINUE USING JSON FOR THE SOLE PURPOSE
    OF TESTING/PLAYING AROUND WITH IT.

    COMMITS CREATED IN THIS STATE WILL BE INCOMPATIBLE
    WITH ONES CREATED USING PYTHON-YAML.

    * * * * * * * * * * * * * * * * * * * * *

    IF YOU ARE *NOT* A HARMQNY DEVELOPER, ABORT NOW AND INSTALL PYTHON-YAML.

    * * * * * * * * * * * * * * * * * * * * *
    """)

    # Harmony uses YaML.
    # As temporary fix for machines where I have no yaml
    # available (and no internet connection, damn!),
    # Use json for unit testing.

    import json

    def read(filename):
        with open(filename, 'r') as f:
            r = json.load(f)
        return r

    def write(d, filename):
        with open(filename, 'w') as f:
            json.dump(d, f)

    def dump(d):
        return json.dumps(d)

else:
    def read(filename):
        r = None
        with open(filename, 'r') as f:
            r = yaml.safe_load(f.read())
        return r

    def write(d, filename):
        with open(filename, 'w') as f:
            yaml.safe_dump(d, f)

    def dump(d):
        return yaml.safe_dump(d)



