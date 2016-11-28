
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)

def cmp_(a, b):
    return (a > b) - (a < b)

def log_set_(s, name):
    logger.debug('{}:'.format(name))
    for e in s:
        logger.debug('  {}'.format(e))
    logger.debug('')

class FileState:

    # TODO: automatically normalize path. Either on string level or
    # ask WorkingDirectory to do it when creating these

    def __init__(self, path = None, digest = None, size = None, mtime = None):
        self.path = path
        self.digest = digest
        self.size = size
        self.mtime = mtime

    def __deepcopy__(self, memo):
        return FileState(
            self.path,
            self.digest,
            self.size,
            self.mtime,
        )

    def __repr__(self):
        return 'FileState({}, digest={}, size={})'.format(
            self.path, self.digest, self.size
        )

    @classmethod
    def from_dict(class_, d):
        return class_(**d)

    def to_dict(self):
        return {
            'path': self.path,
            'digest': self.digest,
            'size': self.size,
            'mtime': self.mtime,
        }

    def contents_different(self, other):
        return self.size != other.size or self.digest != other.digest

    #def compare_clock(self, other):
        #logger.debug('compare_clock({}, {})'.format(self, other))

        #keys = set(self.clock.keys()).union(other.clock.keys())

        #sign = 0
        #for k in keys:
            #new_sign = cmp_(self.clock.get(k, 0), other.clock.get(k, 0))
            #logger.debug('compare_clock k={} self={} other={} sign={}'.format(
                #k, self.clock.get(k, 0), other.clock.get(k, 0), new_sign
            #))
            #if sign == 0:
                #sign = new_sign
            #elif new_sign == -sign:
                #logger.debug('uncomparable: {} {} k={}'.format(self, other, k))
                #return None

        #logger.debug('-> {}'.format(sign))
        #return sign


    #@classmethod
    #def get_heads(self, states):
        #"""
        #Return all "maximal" entries (acc. to their vector clock),
        #that is all the entries that are not cause for any others
        #"""
        #unseen = set(states)
        #candidates = set(states)

        #while unseen:
            #log_set_(unseen, 'unseen')
            #log_set_(candidates, 'candidates')


            #entry = unseen.pop()
            #logger.debug('entry: {}'.format(entry))

            ## Now remove all entries in s that are "lower" than entry
            #to_remove = set(e for e in candidates if e.compare_clock(entry) == -1)

            #log_set_(to_remove, 'to_remove')

            #candidates -= to_remove
            #unseen -= to_remove
        #return candidates



