import os
import pytest

from pathlib import Path

from qywps.utils.qgis import start_qgis_application, setup_qgis_paths

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

    from qywps.utils.plugins import WPSServerInterfaceImpl
    
    rootdir  = Path(session.config.rootdir.strpath)
    settings = { "Processing/Configuration/SCRIPTS_FOLDERS": str(rootdir / 'scripts') }

    global qgis_application
    qgis_application = start_qgis_application(enable_processing=True, cleanup=False, 
                                   settings=settings)
    try:
        iface = WPSServerInterfaceImpl(str(rootdir), with_scripts=True)
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


def pytest_configure(config):
    pass 

