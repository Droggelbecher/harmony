
import hashlib

DEFAULT = 'sha1'

def get_hasher(h):
    def hasher(s):
        return h + ':' + getattr(hashlib, h)(s).hexdigest()
    return hasher


