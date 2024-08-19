"""
    Test server disponibility
"""
import requests


def test_root_request(host):
    """ Test response from root path
    """
    rv = requests.get(host + "/")
    assert rv.status_code == 200
