import pytest
import os
from string import Template


_baseurl = None

class Data(object):
    def __init__(self, request):
        self.rootdir = request.config.rootdir.join('data')

    def open(self, path, mode='rb'):
        return self.rootdir.join(path).open(mode)

    def open_template(self, path, **kwds):
        with self.rootdir.join(path).open('r') as tpl:
            return Template(tpl.read()).substitute(kwds, DATADIR=self.datadir.strpath)


@pytest.fixture()
def host(request):
    return _baseurl


@pytest.fixture(scope='session')
def data(request):
    return Data(request)


def pytest_addoption(parser):
    parser.addoption("--host", metavar="HOST", default="http://localhost:8080")


def pytest_configure(config):
    global _baseurl
    _baseurl = config.getoption('host')+"/ows/"

