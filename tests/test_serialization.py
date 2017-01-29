
import logging
from harmony.serialization import Serializable


logger = logging.getLogger(__name__)


class Dummy(Serializable):
    def __init__(self, i, s, l, d):
        self.i = i
        self.s = s
        self.l = l
        self.d = d

    def __eq__(self, other):
        return self.i == other.i \
            and self.s == other.s \
            and self.l == other.l \
            and self.d == other.d

def test_dict_conversion():

    t1 = Dummy(
        i = 123,
        s = "Foobar",
        l = [ [], [1, []], [2, [1, []]] ],
        d = {
            'foo': 'bar',
            3: 4,
            'x': [1, 2, 3],
            },
    )

    d = t1.to_dict()
    t2 = Dummy.from_dict(d)

    assert t1 == t2

