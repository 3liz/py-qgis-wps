##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# Author: Calin Ciociu                                           #
#                                                                #  
# Copyrigth 2018 3liz                                            #
# Author: David Marteau                                          #
#                                                                #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

"""
Reads the PyWPS configuration file
"""

import logging
import sys
import os
import tempfile
import qywps

import configparser

CONFIG = None
LOGGER = logging.getLogger("QYWPS")


def get_config(section):
    """ Return the configuration section
    """
    if CONFIG is None:
        load_configuration()

    return CONFIG[section]


def load_configuration():
    """Load PyWPS configuration from configuration file.

    :param cfgfile: path to the configuration file
    :param cfgdefault: default configuration dict
    :param cfgdict: configuration dict (override file and default)
    """

    global CONFIG

    LOGGER.info('loading configuration')
    CONFIG = configparser.ConfigParser()

    getenv = os.environ.get

    LOGGER.debug('setting default values')
    CONFIG.add_section('server')
    CONFIG.set('server', 'logstorage' , getenv('QYWPS_SERVER_LOGSTORAGE','REDIS'))
    CONFIG.set('server', 'encoding', 'utf-8')
    CONFIG.set('server', 'language', 'en-US')
    CONFIG.set('server', 'url', '{host_url}')
    CONFIG.set('server', 'maxsingleinputsize', '1mb')
    CONFIG.set('server', 'temp_path', tempfile.gettempdir())
    outputpath = tempfile.gettempdir()
    CONFIG.set('server', 'outputpath'           , getenv('QYPWS_OUTPUTPATH',outputpath))
    CONFIG.set('server', 'store_url'            , '{host_url}store/{uuid}/{file}?service=WPS')
    CONFIG.set('server', 'status_url'           , '{host_url}ows/?service=WPS&request=GetResults&uuid={uuid}') 
    CONFIG.set('server', 'workdir'              , getenv('QYWPS_SERVER_WORKDIR',tempfile.gettempdir()))
    CONFIG.set('server', 'host_proxy'           , getenv('QYWPS_SERVER_HOST_PROXY',''))
    CONFIG.set('server', 'parallelprocesses'    , getenv('QYWPS_SERVER_PARALLELPROCESSES','1'))
    CONFIG.set('server', 'response_timeout'     , getenv('QYWPS_SERVER_RESPONSE_TIMEOUT','600'))
    CONFIG.set('server', 'response_expiration'  , getenv('QYWPS_SERVER_RESPONSE_EXPIRATION','86400'))
    CONFIG.set('server', 'wms_service_url'      , getenv('QYWPS_SERVER_WMS_SERVICE_URL','{host_url}'))
    CONFIG.set('server', 'wps_result_map_uri'   , getenv('QYWPS_SERVER_RESULTS_MAP_URI','wps-results:'))
    CONFIG.set('server', 'wms_response_uri'     , '%(wms_service_url)s?MAP=%(wps_result_map_uri)s{uuid}/{name}.qgs&service=WMS&request=GetCapabilities')
    CONFIG.set('server', 'cleanup_interval'     ,'600')

    CONFIG.set('server', 'outputurl'            , '%(store_url)s')
    CONFIG.set('server', 'download_ttl'         , getenv('QYWPS_DOWNLOAD_TTL','30'))
 
    CONFIG.add_section('logging')
    CONFIG.set('logging', 'level', getenv('QYWPS_LOGLEVEL','INFO'))

    CONFIG.add_section('logstorage:db')
    CONFIG.set('logstorage:db', 'database', 'sqlite:///:memory:')
    CONFIG.set('logstorage:db', 'prefix', 'qywps_')

    CONFIG.add_section('logstorage:redis')
    CONFIG.set('logstorage:redis', 'host' , getenv('QYWPS_REDIS_HOST','localhost'))
    CONFIG.set('logstorage:redis', 'port' , getenv('QYWPS_REDIS_PORT','6379'))
    CONFIG.set('logstorage:redis', 'dbnum', getenv('QYWPS_REDIS_DBNUM','0')) 
 
    CONFIG.add_section('cache')
    CONFIG.set('cache', 'size' , '10' )
    CONFIG.set('cache', 'rootdir' , getenv('QYWPS_CACHE_ROOTDIR',''))

    CONFIG.add_section('processing')
    CONFIG.set('processing', 'providers', getenv('QYWPS_PROCESSSING_PROVIDERS',''))
    CONFIG.set('processing', 'providers_module_path', getenv('QYWPS_PROCESSSING_PROVIDERS_MODULE_PATH',''))

    CONFIG.add_section('metadata:main')
    CONFIG.set('metadata:main', 'identification_title', 'QyWPS Processing Service')
    CONFIG.set('metadata:main', 'identification_abstract', 'QyWPS is an implementation of the Web Processing Service standard from the Open Geospatial Consortium. QyWPS is written in Python.')  # noqa
    CONFIG.set('metadata:main', 'identification_keywords', 'QyWPS,WPS,OGC,QGIS,processing')
    CONFIG.set('metadata:main', 'identification_keywords_type', 'theme')
    CONFIG.set('metadata:main', 'identification_fees', 'NONE')
    CONFIG.set('metadata:main', 'identification_accessconstraints', 'NONE')
    CONFIG.set('metadata:main', 'provider_name', 'Organization Name')
    CONFIG.set('metadata:main', 'provider_url', 'http://qywps.org/')
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
    CONFIG.read_file(cfgfile)
    LOGGER.info('Configuration file <%s> loaded', cfgfile)


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
        LOGGER.error('server->%s configuration value %s is not directory' % (confid, confvalue))
        raise ValueError(confvalue)

    if not os.path.isabs(confvalue):
        LOGGER.error('server->%s configuration value %s is not absolute path' % (confid, confvalue))
        raise ValueError(confvalue)

    CONFIG.set(confname, confid, confvalue)


def get_size_mb(mbsize):
    """Get real size of given obeject

    """

    size = mbsize.lower()

    import re

    units = re.compile("[gmkb].*")
    newsize = float(re.sub(units, '', size))

    if size.find("g") > -1:
        newsize *= 1024
    elif size.find("m") > -1:
        newsize *= 1
    elif size.find("k") > -1:
        newsize /= 1024
    else:
        newsize *= 1
    LOGGER.debug('Calculated real size of %s is %s', mbsize, newsize)
    return newsize

