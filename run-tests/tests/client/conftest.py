import pytest
import os
from string import Template


_baseurl = None


@pytest.fixture()
def host(request):
    return _baseurl


def pytest_addoption(parser):
    parser.addoption("--host", metavar="HOST", default="http://localhost:8888")


def pytest_configure(config):
    global _baseurl
    _baseurl = config.getoption('host')+"/ows/"

