
import hashlib

DEFAULT = 'sha1'

def get_hasher(h):
    if h == 'default':
        h = DEFAULT
    def hasher(s):
        return h + ':' + getattr(hashlib, h)(s).hexdigest()
    return hasher


