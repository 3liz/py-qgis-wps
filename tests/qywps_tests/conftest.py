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


@pytest.fixture(scope='session')
def application(request):
    setup_qgis_paths()
    from qywps.utils.processing import WPSServerInterfaceImpl
    qappl = start_qgis_application(enable_processing=True, cleanup=False)
    try:
        
        iface = WPSServerInterfaceImpl(request.config.rootdir.strpath)
        iface.initialize()
        assert len(iface.plugins) > 0

        iface.register_providers()
        assert len(list(iface.providers)) > 0
        
        qappl.__IFACE = iface
        
    except Exception as e:
        qappl.exitQgis()
        pytest.exit("Failed to initialize provider %s:" %e)

    request.addfinalizer(lambda: qappl.exitQgis())
    return qappl

def pytest_configure(config):
    pass 

