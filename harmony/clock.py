
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
        """
        Compare with other clock instance.
        Return:
            -1: self is lower than other
             0: self and other are equal
             1: self is greater than other
            None: self and other are not comparable.
        """
        keys = set(self.values.keys()).union(other.values.keys())

        sign = 0
        for k in keys:
            new_sign = cmp_(self.values.get(k, 0), other.values.get(k, 0))
            if sign == 0:
                sign = new_sign
            elif new_sign == -sign:
                return None

        return sign

    def update(self, other):
        """
        Update based on other clock instance.
        Return a new clock instance with values being the maximum of self and other.
        """
        for k in set(self.values.keys()) | set(other.values.keys()):
            self.values[k] = max(
                self.values.get(k, 0),
                other.values.get(k, 0)
            )

    def increase(self, k):
        self.values[k] = self.values.get(k, 0) + 1

    def comparable(self, other):
        return self.compare(other) is not None

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
