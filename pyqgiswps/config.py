#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Original parts are Copyright 2016 OSGeo Foundation,            
# represented by PyWPS Project Steering Committee,               
# and released under MIT license.                                
# Please consult PYWPS_LICENCE.txt for details
# Original Author: Calin Ciociu                                           
#

"""
Reads the PyWPS configuration file
"""

import logging
import sys
import os
import tempfile
import functools
import pyqgiswps

import configparser

from typing import Any


CONFIG = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
CONFIG.optionxform = lambda opt: opt

def _log( *args ):
    print( *args, file=sys.stderr, flush=True)


def get_config(section=None):
    """ Return the configuration section
    """
    if CONFIG is None:
        load_configuration()

    return CONFIG[section] if section else CONFIG
    

def set_config(section, name, value):
    """ Set configuration value
    """
    CONFIG.set(section, name , value)


def load_configuration():
    """Load PyWPS configuration from configuration file.

    :param cfgfile: path to the configuration file
    :param cfgdefault: default configuration dict
    :param cfgdict: configuration dict (override file and default)
    """

    CONFIG.clear()

    _log('loading configuration')
    getenv = os.getenv

    #
    # Server
    #

    CONFIG.add_section('server')
    CONFIG.set('server', 'encoding', 'utf-8')
    CONFIG.set('server', 'language', 'en-US')
    CONFIG.set('server', 'url', '{host_url}')
    # Select if output files are returned by reference or in response body
    CONFIG.set('server', 'outputfile_as_reference', getenv('QGSWPS_SERVER_OUTPUTFILE_AS_REFERENCE', 'yes'))
    # Max input file fetched as remote reference
    CONFIG.set('server', 'maxinputsize'         , getenv('QGSWPS_SERVER_MAXINPUTSIZE' ,'100m'))
    # Max request size 
    CONFIG.set('server', 'maxbuffersize'        , getenv('QGSWPS_SERVER_MAXBUFFERSIZE','1m'))
    # Storage url for retrieving reference files
    CONFIG.set('server', 'store_url'            , '{host_url}store/{uuid}/{file}?service=WPS')
    # URL for retrieving status
    CONFIG.set('server', 'status_url'           , '{host_url}ows/?service=WPS&request=GetResults&uuid={uuid}') 
    # Path to workdir where process are executed"
    CONFIG.set('server', 'workdir'              , getenv('QGSWPS_SERVER_WORKDIR',tempfile.gettempdir()))
    # Configure host if the server is behind a proxy
    CONFIG.set('server', 'host_proxy'           , getenv('QGSWPS_SERVER_HOST_PROXY',''))
    # Number of parallel processes that are allowed to run algorithms
    CONFIG.set('server', 'parallelprocesses'    , getenv('QGSWPS_SERVER_PARALLELPROCESSES','1'))
    # Maximal number of executions can run in the same worker before beeing restarted
    CONFIG.set('server', 'processlifecycle'     , getenv('QGSWPS_SERVER_PROCESSLIFECYCLE','1'))
    # Maximal number of waiting tasks - extra tasks will return a 509 in synchronous execution
    CONFIG.set('server', 'maxqueuesize'         , getenv('QGSWPS_SERVER_MAXQUEUESIZE','100'))
    # Timeout for tasks execution
    CONFIG.set('server', 'response_timeout'     , getenv('QGSWPS_SERVER_RESPONSE_TIMEOUT','1800'))
    # Expiration time in Redis cache for task responses
    CONFIG.set('server', 'response_expiration'  , getenv('QGSWPS_SERVER_RESPONSE_EXPIRATION','86400'))
    # Base url used for return WMS references (Qgis projects holding layers created by WPS tasks)
    CONFIG.set('server', 'wms_service_url'      , getenv('QGSWPS_SERVER_WMS_SERVICE_URL','{host_url}'))
    # Base uri used for the MAP argument in WMS references
    CONFIG.set('server', 'wps_result_map_uri'   , getenv('QGSWPS_SERVER_RESULTS_MAP_URI','wps-results:'))
    # Full URL used for returning  WPS references
    CONFIG.set('server', 'wms_response_uri'     , '${wms_service_url}?MAP=${wps_result_map_uri}{uuid}/{name}.qgs&service=WMS&request=GetCapabilities')
    # Cleanup interval in seconds
    CONFIG.set('server', 'cleanup_interval'     ,'600')
    # Download API expiration ttl for a download URL
    CONFIG.set('server', 'download_ttl'         , getenv('QGSWPS_DOWNLOAD_TTL','30'))
    # Enable middleware filters from extensions
    CONFIG.set('server', 'enable_filters'       , getenv('QGSWPS_SERVER_ENABLE_FILTERS', 'yes'))

    #
    # Logging
    #

    CONFIG.add_section('logging')
    CONFIG.set('logging', 'level', getenv('QGSWPS_LOGLEVEL','INFO'))

    #
    # Log storage
    #

    CONFIG.add_section('logstorage:redis')
    CONFIG.set('logstorage:redis', 'host'  , getenv('QGSWPS_REDIS_HOST'  ,'localhost'))
    CONFIG.set('logstorage:redis', 'port'  , getenv('QGSWPS_REDIS_PORT'  ,'6379'))
    CONFIG.set('logstorage:redis', 'dbnum' , getenv('QGSWPS_REDIS_DBNUM' ,'0')) 
    CONFIG.set('logstorage:redis', 'prefix', getenv('QGSWPS_REDIS_PREFIX','pyqgiswps')) 

    #
    # Projects cache
    #

    CONFIG.add_section('projects.cache')
    # Maximun number of projects in cache
    CONFIG.set('projects.cache', 'size'    , getenv('QGSWPS_CACHE_SIZE','10' ))
    # Root directory for projects file
    CONFIG.set('projects.cache', 'rootdir' , getenv('QGSWPS_CACHE_ROOTDIR',''))
    # Ensure that loaded project is valid before loading in cache
    CONFIG.set('projects.cache', 'strict_check' , getenv('QGSWPS_CACHE_STRICT_CHECK','yes'))

    CONFIG.add_section('projects.schemes')

    # XXX Legacy section
    CONFIG.add_section('cache')
    CONFIG.set('cache', 'size'    , '${projects.cache:size}')
    CONFIG.set('cache', 'rootdir' , '${projects.cache:rootdir}')
    CONFIG.set('cache', 'strict_check' , '${projects.cache:strict_check}')

    #
    # Processing
    #

    CONFIG.add_section('processing')
    CONFIG.set('processing', 'providers_module_path', getenv('QGSWPS_PROCESSING_PROVIDERS_MODULE_PATH',''))
    CONFIG.set('processing', 'exposed_providers'    , getenv('QGSWPS_PROCESSING_EXPOSED_PROVIDERS' ,'script,model'))
    CONFIG.set('processing', 'accesspolicy'         , getenv('QGSWPS_PROCESSING_ACCESSPOLICY' ,'${providers_module_path}/accesspolicy.yml'))

    #
    # Qgis folders settings
    # 
    # Enable to define search folder list with globbing patterns
    # to be expanded in Qgis settings
    #
    CONFIG.add_section('qgis.settings.folders')
    CONFIG.set('qgis.settings.folders', 'Processing/Configuration/SCRIPTS_FOLDERS', '${processing:providers_module_path}/scripts')
    CONFIG.set('qgis.settings.folders', 'Processing/Configuration/MODELS_FOLDER'  , '${processing:providers_module_path}/models')

    #
    # Metadata
    #

    CONFIG.add_section('metadata:main')
    CONFIG.set('metadata:main', 'identification_title', 'Py-Qgis-WPS Processing Service')
    CONFIG.set('metadata:main', 'identification_abstract', 'Py-Qgis-WPS is an implementation of the Web Processing Service standard from the Open Geospatial Consortium. Py-Qgis-WPS is written in Python.')  # noqa
    CONFIG.set('metadata:main', 'identification_keywords', 'Py-Qgis-WPS,WPS,OGC,QGIS,processing')
    CONFIG.set('metadata:main', 'identification_keywords_type', 'theme')
    CONFIG.set('metadata:main', 'identification_fees', 'NONE')
    CONFIG.set('metadata:main', 'identification_accessconstraints', 'NONE')
    CONFIG.set('metadata:main', 'provider_name', 'Organization Name')
    CONFIG.set('metadata:main', 'provider_url', 'https://github.com/3liz/py-qgis-wps')
    CONFIG.set('metadata:main', 'contact_name', 'Lastname, Firstname')
    CONFIG.set('metadata:main', 'contact_address', 'Mailing Address')
    CONFIG.set('metadata:main', 'contact_email', 'Email Address')
    CONFIG.set('metadata:main', 'contact_url', 'Contact URL')
    CONFIG.set('metadata:main', 'contact_role', 'pointOfContact')


def read_config_dict( userdict ):
    """ Read configuration from dictionary

        Will override previous settings
    """
    CONFIG.read_dict( userdict )


def read_config_file( cfgfile ):
    """ Read configuration from file
    """
    cfgfile = os.path.abspath(cfgfile)
    with open(cfgfile, mode='rt') as fp:
        CONFIG.read_file(fp)
    _log('Configuration file <%s> loaded' % cfgfile)


def config_to_dict():
    """ Convert actual configuration to dictionary
    """
    return { s: dict(p.items()) for s,p in CONFIG.items() }


def validate_config_path(confname, confid, optional=False):
    """ Validate directory path
    """
    confvalue = get_config(confname).get(confid,'')

    if not confvalue and optional:
        return

    confvalue = os.path.normpath(confvalue)
    if not os.path.isdir(confvalue):
        _log('ERROR: server->%s configuration value %s is not directory' % (confid, confvalue))
        raise ValueError(confvalue)

    if not os.path.isabs(confvalue):
        _log('ERROR: server->%s configuration value %s is not absolute path' % (confid, confvalue))
        raise ValueError(confvalue)

    CONFIG.set(confname, confid, confvalue)


def get_size_bytes(size):
    """Get real size of given obeject

    """
    size = size.lower()

    import re

    units = re.compile("[gmkb].*")
    newsize = float(re.sub(units, '', size))

    if size.find("g") > -1:
        newsize *= 1024 * 1024 * 1024
    elif size.find("m") > -1:
        newsize *= 1024 * 1024
    elif size.find("k") > -1:
        newsize *= 1024
    else:
        newsize *= 1
    return newsize


#
# Published services
#
from pyqgisservercontrib.core import componentmanager

NO_DEFAULT=object()

# Chars that are to be replaced in env variable name
ENV_REPLACE_CHARS=':.-@#$%&*'

@componentmanager.register_factory('@3liz.org/config-service;1')
class ConfigService:
    """ Act as a proxy
    """

    def __init__(self):
        self.allow_env = True

    def __get_impl( self, _get_fun, section:str, option:str, fallback:Any = NO_DEFAULT ) -> Any:
        """
        """
        value = _get_fun(section, option, fallback=NO_DEFAULT)
        if value is NO_DEFAULT:
            # Look in environment
            # Note that the section must exists
            if self.allow_env:
                varname  = 'QGSWPS_%s_%s' % (section.upper(), option.upper())
                varname  = functools.reduce( lambda s,c: s.replace(c,'_'), ENV_REPLACE_CHARS, varname)
                varvalue = os.getenv(varname)
                if varvalue is not None:
                    CONFIG.set(section, option, varvalue)
                # Let config parser translate the value for us
                value = _get_fun(section, option, fallback=fallback)
            else:
                value = fallback
        if value is NO_DEFAULT:
            raise KeyError('[%s] %s' % (section,option))
        return value


    get        = functools.partialmethod(__get_impl,CONFIG.get)
    getint     = functools.partialmethod(__get_impl,CONFIG.getint)
    getboolean = functools.partialmethod(__get_impl,CONFIG.getboolean)
    getfloat   = functools.partialmethod(__get_impl,CONFIG.getfloat)

    def __getitem__(self, section):
        return CONFIG[section]

    def __contains__(self, section):
        return section in CONFIG

    def set( self, section:str, option:str, value: Any ) -> None:
        CONFIG.set( section, option, value )

    def add_section( self, sectionname: str ) -> None:
        # We do not care if the section already exists
        try:
            CONFIG.add_section( sectionname )
        except configparser.DuplicateSectionError:
            pass 


confservice = ConfigService()


