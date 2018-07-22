
import hashlib
import warnings
from typing import Callable
from typing.io import BinaryIO

DEFAULT = 'sha1'
BLOCKSIZE = 1024 ** 2

def get_hasher(h: str) -> Callable[[BinaryIO], str]:
    """
    Given a hashlib hasher name, return a function
    that computes the hash for any filelike object, returning its digest as a string.
    If $h is 'default', choose a default hash function.
    """

    if h == 'default':
        h = DEFAULT

    try:
        hashlib_hasher = getattr(hashlib, h)()
    except AttributeError:
        raise ValueError('Hasher "{}" not found in hashlib.'.format(h))


    def hasher(s):
        if hasattr(s, 'read'):
            for block in iter(lambda: s.read(BLOCKSIZE), b''):
                hashlib_hasher.update(block)
            digest = hashlib_hasher.hexdigest()
        else:
            warnings.warn('You should call a hasher with a file-like.', DeprecationWarning)
            hashlib_hasher.update(s)
            digest = hashlib_hasher.hexdigest()

        return f'{h}:{digest}'

    return hasher

# vim: ts=4 sw=4:
