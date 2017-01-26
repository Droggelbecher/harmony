
import logging
from harmony.clock import Clock


logger = logging.getLogger(__name__)

def test_clock_construction():
    # Smoke test
    c1 = Clock(a = 10, b = 2, c = -23)
    c2 = Clock()

def test_clock_compare_equal():

    assert Clock() == Clock()
    assert Clock(a = 0) == Clock()
    assert Clock() == Clock(a = 0)
    assert Clock() == Clock(a = 0, b = 0)
    assert Clock() == Clock(z = 0, cc = 0, b = 0)
    assert Clock(a = 0) == Clock(b = 0)
    assert Clock(a = 1) == Clock(a = 1)
    assert Clock(a = 23) == Clock(a = 23)
    assert Clock(a = 23) == Clock(a = 23, b = 0)
    assert Clock(a = 23, x = 67, c = 3, b = 0) == Clock(c = 3, x = 67, a = 23, zz = 0, ya = 0)


def test_clock_compare_lower():

    assert Clock()      < Clock(a = 1)
    assert Clock(a = 1) < Clock(a = 1, b = 1)
    assert Clock(a = 1) < Clock(a = 2)
    assert Clock(a = 1) < Clock(a = 2, b = 1)

def test_clock_compare_greater():

    assert Clock(a = 1)        >  Clock()      
    assert Clock(a = 1, b = 1) >  Clock(a = 1) 
    assert Clock(a = 2)        >  Clock(a = 1) 
    assert Clock(a = 2, b = 1) >  Clock(a = 1) 

