import os
import sys
import logging
import pytest

from pathlib import Path

from pyqgiswps.tests import TestRuntime

def pytest_addoption(parser):
    parser.addoption("--server-log-level", choices=['all','debug', 'info', 'warning', 'error','critical'] , help="log level",
                     default='error')

server_log_level = None

def pytest_configure(config):
    global server_log_level
    server_log_level = config.getoption('server_log_level')


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

    if server_log_level != 'all':
        log_level = getattr(logging, server_log_level.upper())
        logging.disable(log_level)

    rt = TestRuntime.instance()
    rt.start()

def pytest_sessionfinish(session, exitstatus):
    """
    """
    rt = TestRuntime.instance()
    rt.stop()


