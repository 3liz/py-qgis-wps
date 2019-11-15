import os
import sys
import logging
import pytest

from pathlib import Path

from pyqgiswps.utils.qgis import start_qgis_application, setup_qgis_paths

def pytest_addoption(parser):
    parser.addoption("--server-log-level", choices=['debug', 'info', 'warning', 'error','critical'] , help="log level",
                     default='warning')

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

qgis_application = None

def pytest_sessionstart(session):
    setup_qgis_paths()

    logging.basicConfig( stream=sys.stderr )

    log_level = getattr(logging, server_log_level.upper())
    logging.disable(log_level)

    logger = logging.getLogger('SRVLOG')
    logger.setLevel(log_level)

    from pyqgiswps.utils.plugins import WPSServerInterfaceImpl
    
    rootdir  = Path(session.config.rootdir.strpath)
    settings = { 
        "Processing/Configuration/SCRIPTS_FOLDERS": str(rootdir / 'scripts'),
        "Processing/Configuration/MODELS_FOLDER"  : str(rootdir / 'models') 
    }

    global qgis_application
    qgis_application = start_qgis_application(enable_processing=True, cleanup=False, 
                                   settings=settings)
    try:
        iface = WPSServerInterfaceImpl(str(rootdir), with_providers=['script','model'])
        iface.initialize()
        assert len(iface.plugins) > 0

        iface.register_providers()
        assert len(list(iface.providers)) > 0
        
        qgis_application.__IFACE = iface
        
    except Exception as e:
        qgis_application.exitQgis()
        pytest.exit("Failed to initialize provider %s:" %e)


def pytest_sessionfinish(session, exitstatus):
    """
    """
    global qgis_application
    qgis_application.exitQgis()
    qgis_application = None


