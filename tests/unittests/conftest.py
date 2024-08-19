from pathlib import Path

import pytest

from pyqgiswps.tests import TestRuntime


def _workdir(request):
    workdir = Path(request.config.rootdir.strpath).parent / '__workdir__'
    workdir.mkdir(exist_ok=True)
    return workdir


def _outputdir(request):
    outdir = Path(request.config.rootdir.strpath) / '__outputdir__'
    outdir.mkdir(exist_ok=True)
    return outdir


def pytest_configure(config):
    pass


@pytest.fixture(scope='session')
def outputdir(request):
    return _outputdir(request)


@pytest.fixture(scope='class')
def outputdir_class(request):
    outdir = _outputdir(request)
    # Make it available in untitests TestCase
    request.cls.outputdir = outdir
    return outdir


@pytest.fixture(scope='session')
def workdir(request):
    return _workdir(request)


@pytest.fixture(scope='class')
def workdir_class(request):
    workdir = _workdir(request)
    request.cls.workdir = workdir
    return workdir


@pytest.fixture(scope='session')
def data(request):
    return Path(request.config.rootdir.strpath) / 'data'


@pytest.fixture(scope='session')
def rootdir(request):
    return Path(request.config.rootdir.strpath)


def pytest_sessionstart(session):

    rt = TestRuntime.instance()
    rt.start()


def pytest_sessionfinish(session, exitstatus):
    """
    """
    rt = TestRuntime.instance()
    rt.stop()
