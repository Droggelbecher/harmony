
import yaml

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

