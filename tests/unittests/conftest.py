import os
import sys
import logging
import pytest

from pathlib import Path

from pyqgiswps.tests import TestRuntime

def pytest_addoption(parser):
    parser.addoption("--server-debug", action='store_true' , help="set debug mode",
                     default=False)

server_debug = False

def pytest_configure(config):
    global server_debug
    server_debug = config.getoption('server_debug')


@pytest.fixture(scope='session')
def outputdir(request):
    outdir=request.config.rootdir.join('__outputdir__')
    os.makedirs(outdir.strpath, exist_ok=True)
    return outdir

@pytest.fixture(scope='session')
def data(request):
    return request.config.rootdir.join('data')

@pytest.fixture(scope='session')
def rootdir(request):
    return request.config.rootdir

def pytest_sessionstart(session):

    logging.basicConfig( stream=sys.stderr, level=logging.DEBUG )

    if not server_debug:
        logging.disable(logging.ERROR)

    rt = TestRuntime.instance()
    rt.start()

def pytest_sessionfinish(session, exitstatus):
    """
    """
    rt = TestRuntime.instance()
    rt.stop()


