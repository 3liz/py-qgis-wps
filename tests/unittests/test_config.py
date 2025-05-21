

def test_size_bytes():
    from pyqgiswps.config import get_size_bytes

    sz = get_size_bytes('1m')
    assert sz == 1048576

    sz = get_size_bytes('512kb')
    assert sz == 524288

    sz = get_size_bytes('2g')
    assert sz == 2147483648


def test_manifest():
    from pyqgiswps import version

    m = version.read_manifest()
    print("\n::test_manifest::", m)
    assert 'commitid' in m
    assert 'buildid' in m
    assert 'version' in m
