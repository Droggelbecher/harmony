
import logging

logger = logging.getLogger(__name__)

def cmp_(a, b):
    return (a > b) - (a < b)

class Clock:

    def __init__(self, **kws):
        self.values = dict(kws)

    def __repr__(self):
        return 'Clock({})'.format(
            ','.join(
                '{} = {!r}'.format(k, v)
                for k, v in self.values.items()
            )
        )

    @classmethod
    def from_dict(class_, d):
        return class_(**d)

    def to_dict(self):
        return self.values

    def compare(self, other):
        keys = set(self.values.keys()).union(other.values.keys())

        sign = 0
        for k in keys:
            new_sign = cmp_(self.values.get(k, 0), other.values.get(k, 0))
            if sign == 0:
                sign = new_sign
            elif new_sign == -sign:
                logger.debug('uncomparable: {} {} k={}'.format(self, other, k))
                return None

        logger.debug('-> {}'.format(sign))
        return sign

    def __lt__(self, other):
        return self.compare(other) == -1

    def __eq__(self, other):
        return self.compare(other) == 0

    def __gt__(self, other):
        return other < self

    def __le__(self, other):
        return (self < other) or (self == other)

    def __ge__(self, other):
        return (self > other) or (self == other)
