#!/usr/bin/env python
#
# http://localhost/pywps/?service=WPS&request=GetCapabilities&version=1.0.0
# http://localhost/pywps/?service=WPS&request=DescribeProcess&version=1.0.0&Identifier=qywps_test:testcopylayer
# http://localhost/pywps/?service=WPS&request=Execute&Identifier=qywps_test:testcopylayer&version=1.0.0&map=france_parts&DATAINPUTS=INPUT=france_parts;OUTPUT=output_layer
#
import os
import sys
import qywps
import logging

from qywps.app import Service
from qywps.executors.processingexecutor import  ProcessingExecutor

LOGGER = logging.getLogger("QYWPS")

# Move to test directory
current_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(os.path.join(current_path,'qywps_tests'))

# Create working directory
workdir    = os.path.join(os.getcwd(),'__outputdir__')
outputpath = os.path.join(os.getcwd(),'__outputpath__')

datadir = os.path.join(os.getcwd(),'data')

os.makedirs(workdir   , exist_ok=True)
os.makedirs(outputpath, exist_ok=True)

sys.path.append(os.getcwd())

config = {
    'server': { 
        'parallelprocesses':2,
        'workdir': workdir,
        'outputpath': outputpath,
    },
    'processing' : { 
        'providers': 'qywps_test',
        'providers_module_path': os.path.join(os.getcwd(),'algorithms'),
    },
    'cache': { 'rootdir': datadir }
}


# XXX We MUST import  providers BEFORE initializing qgisapp
#from algorithms.TestAlgorithmProvider import  TestAlgorithmProvider

def check_providers(application): 
    registry = application.processingRegistry()
    provider = registry.providerById('qywps_test')
    assert provider is not None
    assert len(provider.algorithms()) > 0
    assert registry.algorithmById('qywps_test:testsimplevalue') is not None
    assert registry.algorithmById('qywps_test:testcopylayer')   is not None

class TestExecutor(ProcessingExecutor):

    def start_qgis(self, main_process):
        qappl = super().start_qgis(main_process)
        if not main_process:
            return
        check_providers(qappl)
        
application = Service(processes=[], cfgdict=config, executor=TestExecutor())

