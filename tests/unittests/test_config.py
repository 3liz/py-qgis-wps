from pyqgiswps.config import get_size_bytes


def test_size_bytes():

    sz = get_size_bytes('1m')
    assert sz == 1048576

    sz = get_size_bytes('512kb')
    assert sz == 524288

    sz = get_size_bytes('2g')
    assert sz == 2147483648
