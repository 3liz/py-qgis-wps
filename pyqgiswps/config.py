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

import configparser
import functools
import os
import sys
import tempfile

from typing import Any

from pyqgisservercontrib.core import componentmanager

CONFIG = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
CONFIG.optionxform = lambda opt: opt

getenv = os.getenv


def _log(*args):
    print(*args, file=sys.stderr, flush=True)  # noqa: T201


def getenv2(env1, env2, default):
    """ Get value from alternate env variable
    """
    value = getenv(env1)
    if value is None:
        value = getenv(env2, default)
    return value


def load_configuration():
    """Load py-qgis-wps configuration from environment

    :param cfgfile: path to the configuration file
    :param cfgdefault: default configuration dict
    :param cfgdict: configuration dict (override file and default)
    """

    CONFIG.clear()

    _log('loading configuration')

    #
    # Server
    #

    CONFIG.add_section('server')
    CONFIG.set('server', 'encoding', 'utf-8')
    CONFIG.set('server', 'language', 'en-US')
    CONFIG.set('server', 'port', getenv('QGSWPS_SERVER_HTTP_PORT', '8080'))
    CONFIG.set('server', 'interfaces', getenv('QGSWPS_SERVER_INTERFACES', '127.0.0.1'))
    # Select if output files are returned by reference or in response body
    CONFIG.set('server', 'outputfile_as_reference', getenv('QGSWPS_SERVER_OUTPUTFILE_AS_REFERENCE', 'yes'))
    # Max input file fetched as remote reference
    CONFIG.set('server', 'maxinputsize', getenv('QGSWPS_SERVER_MAXINPUTSIZE', '100m'))
    # Max request size
    CONFIG.set('server', 'maxbuffersize', getenv('QGSWPS_SERVER_MAXBUFFERSIZE', '1m'))
    # Path to workdir where process are executed"
    CONFIG.set('server', 'workdir', getenv('QGSWPS_SERVER_WORKDIR', tempfile.gettempdir()))
    # Configure host if the server is behind a proxy
    CONFIG.set('server', 'proxy_url', getenv('QGSWPS_SERVER_PROXY_URL', ''))
    # Allow proxyfication
    CONFIG.set('server', 'http_proxy', getenv('QGSWPS_SERVER_HTTP_PROXY', 'yes'))
    # Number of parallel processes that are allowed to run algorithms
    CONFIG.set('server', 'parallelprocesses', getenv('QGSWPS_SERVER_PARALLELPROCESSES', '1'))
    # Maximal number of executions can run in the same worker before beeing restarted
    CONFIG.set('server', 'processlifecycle', getenv('QGSWPS_SERVER_PROCESSLIFECYCLE', '1'))
    # Maximal number of waiting tasks - extra tasks will return a 509 in synchronous execution
    CONFIG.set('server', 'maxqueuesize', getenv('QGSWPS_SERVER_MAXQUEUESIZE', '100'))
    # Timeout for tasks execution
    CONFIG.set('server', 'response_timeout', getenv('QGSWPS_SERVER_RESPONSE_TIMEOUT', '1800'))
    # Expiration time in Redis cache for task responses
    CONFIG.set('server', 'response_expiration', getenv('QGSWPS_SERVER_RESPONSE_EXPIRATION', '86400'))
    # XXX DEPRECATED Base url used for return WMS references (QGIS projects holding layers created by WPS tasks)
    CONFIG.set('server', 'wms_service_url', getenv('QGSWPS_SERVER_WMS_SERVICE_URL', '${wps.request:host_url}'))
    # Base url used for return OWS references (QGIS projects holding layers created by WPS tasks)
    CONFIG.set('server', 'ows_service_url', getenv('QGSWPS_SERVER_OWS_SERVICE_URL', '${wms_service_url}'))
    # Base uri used for the MAP argument in WMS references
    CONFIG.set('server', 'wps_result_map_uri', getenv('QGSWPS_SERVER_RESULTS_MAP_URI', 'wps-results:'))
    # Full URL used for returning  WPS references
    CONFIG.set('server', 'wms_response_url', '${ows_service_url}?MAP={map_url}&service=WMS&request=GetCapabilities')
    # Cleanup interval in seconds
    CONFIG.set('server', 'cleanup_interval', '600')
    # Download API expiration ttl for a download URL
    CONFIG.set('server', 'download_ttl', getenv('QGSWPS_DOWNLOAD_TTL', '30'))
    # Enable middleware filters from extensions
    CONFIG.set('server', 'enable_filters', getenv('QGSWPS_SERVER_ENABLE_FILTERS', 'no'))
    # Path for pre-installed extensions
    CONFIG.set('server', 'sys_config_path', getenv('QGSWPS_SYS_CONFIG_PATH', '/usr/share/qgis_wps'))
    CONFIG.set('server', 'cross_origin', getenv('QGSWPS_SERVER_CROSS_ORIGIN', 'yes'))
    CONFIG.set('server', 'restartmon', getenv('QGSWPS_SERVER_RESTARTMON', ''))
    # SSL configuration
    CONFIG.set('server', 'ssl', getenv('QGSWPS_SERVER_SSL', 'no'))
    CONFIG.set('server', 'ssl_cert', getenv('QGSWPS_SERVER_SSL_CERT', ''))
    CONFIG.set('server', 'ssl_key', getenv('QGSWPS_SERVER_SSL_KEY', ''))

    # Administrator token realm for accessing job list with ogc api
    CONFIG.set('server', 'admin_realm', getenv('QGSWPS_SERVER_ADMIN_REALM', ''))
    CONFIG.set('server', 'enable_job_realm', getenv('QGSWPS_SERVER_ENABLE_JOB_REALM', 'no'))

    # Expose server infos
    CONFIG.set('server', 'expose_server_infos', getenv('QGSWPS_EXPOSE_SERVER_INFOS', 'no'))

    #
    # Logging
    #

    CONFIG.add_section('logging')
    CONFIG.set('logging', 'level', getenv('QGSWPS_LOGLEVEL', 'INFO'))

    #
    # Log storage
    #

    CONFIG.add_section('logstorage:redis')
    CONFIG.set('logstorage:redis', 'host', getenv('QGSWPS_REDIS_HOST', 'localhost'))
    CONFIG.set('logstorage:redis', 'port', getenv('QGSWPS_REDIS_PORT', '6379'))
    CONFIG.set('logstorage:redis', 'dbnum', getenv('QGSWPS_REDIS_DBNUM', '0'))
    CONFIG.set('logstorage:redis', 'prefix', getenv('QGSWPS_REDIS_PREFIX', 'pyqgiswps'))

    #
    # Projects cache
    #
    CONFIG.add_section('projects.cache')
    # Maximun number of projects in cache
    CONFIG.set('projects.cache', 'size', getenv('QGSWPS_CACHE_SIZE', '10'))
    # Root directory for projects file
    CONFIG.set('projects.cache', 'rootdir', getenv('QGSWPS_CACHE_ROOTDIR', ''))
    # Ensure that loaded project is valid before loading in cache
    CONFIG.set('projects.cache', 'strict_check', getenv('QGSWPS_CACHE_STRICT_CHECK', 'yes'))
    CONFIG.set('projects.cache', 'trust_layer_metadata',
               getenv2('QGSWPS_TRUST_LAYER_METADATA', 'QGIS_SERVER_TRUST_LAYER_METADATA', 'no'))
    CONFIG.set('projects.cache', 'disable_getprint',
               getenv2('QGSWPS_DISABLE_GETPRINT', 'QGIS_SERVER_DISABLE_GETPRINT', 'no'))

    CONFIG.set('projects.cache', 'allow_storage_schemes', getenv('QGSWPS_CACHE_ALLOW_STORAGE_SCHEMES', '*'))

    #
    CONFIG.add_section('projects.schemes')

    #
    # Processing
    #
    CONFIG.add_section('processing')
    CONFIG.set('processing', 'providers_module_path', getenv('QGSWPS_PROCESSING_PROVIDERS_MODULE_PATH', ''))
    CONFIG.set('processing', 'exposed_providers', getenv('QGSWPS_PROCESSING_EXPOSED_PROVIDERS', 'script,model'))
    CONFIG.set('processing', 'accesspolicy', getenv(
        'QGSWPS_PROCESSING_ACCESSPOLICY', '${providers_module_path}/accesspolicy.yml'))
    CONFIG.set('processing', 'default_module_path', '${server:sys_config_path}/processing')
    # Define default format used as file destination, use Qgis default if not
    # specified
    CONFIG.set('processing', 'vector.fileext', getenv('QGSWPS_PROCESSING_VECTOR_FILEEXT', ''))
    CONFIG.set('processing', 'raster.fileext', getenv('QGSWPS_PROCESSING_RASTER_FILEEXT', ''))
    # Allow passing the wps parameter directly as file/uri sink in destination parameter
    # Warning this is an **UNSAFE OPTION**, do not allow if you are exposing the service
    # publicly or with concurrent running jobs.
    # Note thar layer name may be specified by appending '|layername=<name>' to the input value
    # Files will be saved under the root path defined by the `[processing] destination_root_path` option.
    CONFIG.set('processing', 'unsafe.raw_destination_input_sink',
               getenv('QGSWPS_PROCESSING_RAW_DESTINATION_INPUT_SINK', 'no'))
    CONFIG.set('processing', 'destination_root_path', getenv('QGSWPS_PROCESSING_DESTINATION_ROOT_PATH', './'))
    #
    # Preference for destination project
    #
    # Force ellipsoid imposed by the src project
    CONFIG.set('processing', 'adjust_ellipsoid', getenv('QGSWPS_PROCESSING_ADJUST_ELLIPSOID', 'no'))
    # Set the CRS to use when no source map is specified
    # For more details on supported formats see OGRSpatialReference::SetFromUserInput()
    CONFIG.set('processing', 'default_crs', getenv('QGSWPS_PROCESSING_DEFAULT_CRS', 'EPSG:4326'))

    #
    # Qgis folders settings
    #
    # Enable to define search folder list with globbing patterns
    # to be expanded in Qgis settings
    #
    CONFIG.add_section('qgis.settings.folders')
    CONFIG.set('qgis.settings.folders', 'Processing/Configuration/SCRIPTS_FOLDERS',
               '${processing:providers_module_path}/scripts')
    CONFIG.set('qgis.settings.folders', 'Processing/Configuration/MODELS_FOLDER',
               '${processing:providers_module_path}/models')

    # Qgis settings
    #
    # Add other Qgis settings
    #
    # XXX Not functional yet
    CONFIG.add_section('qgis.settings')

    #
    # Qgis projects
    #
    CONFIG.add_section('qgis.projects')
    # Set this to force the the advertised OWS urls in the Qgis projects
    # created by pyqgiswps
    CONFIG.set('qgis.projects', 'advertised_ows_url', getenv('QGSWPS_ADVERTISED_OWS_URL', '${server:ows_service_url}'))

    #
    # Metadata
    #
    CONFIG.add_section('metadata')
    CONFIG.set('metadata', 'identification_fees', 'NONE')
    CONFIG.set('metadata', 'identification_accessconstraints', 'NONE')
    CONFIG.set('metadata', 'provider_name', 'Organization Name')
    CONFIG.set('metadata', 'provider_url', 'https://github.com/3liz/py-qgis-wps')
    CONFIG.set('metadata', 'contact_name', 'Lastname, Firstname')
    CONFIG.set('metadata', 'contact_address', 'Mailing Address')
    CONFIG.set('metadata', 'contact_email', 'Email Address')
    CONFIG.set('metadata', 'contact_url', 'Contact URL')
    CONFIG.set('metadata', 'contact_role', 'pointOfContact')
    CONFIG.set('metadata', 'licence_url', 'http://mozilla.org/MPL/2.0/')
    CONFIG.set('metadata', 'licence_name', 'Mozilla Public Licences, v2.0')

    # OWS metadata
    CONFIG.add_section('metadata:ows')
    CONFIG.set('metadata:ows', 'identification_title', 'Py-Qgis-WPS Processing Service')
    CONFIG.set('metadata:ows', 'identification_abstract',
               'Py-Qgis-WPS is an implementation of the Web '
               'Processing Service standard from the Open Geospatial Consortium.')
    CONFIG.set('metadata:ows', 'identification_keywords', 'Py-Qgis-WPS,WPS,OGC,QGIS,processing')
    CONFIG.set('metadata:ows', 'identification_keywords_type', 'theme')
    CONFIG.set('metadata:ows', 'identification_fees', '${metadata:identification_fees}')
    CONFIG.set('metadata:ows', 'identification_accessconstraints', '${metadata:identification_accessconstraints}')
    CONFIG.set('metadata:ows', 'provider_name', '${metadata:provider_name}')
    CONFIG.set('metadata:ows', 'provider_url', '${metadata:provider_url}')
    CONFIG.set('metadata:ows', 'contact_name', '${metadata:contact_name}')
    CONFIG.set('metadata:ows', 'contact_address', '${metadata:contact_address}')
    CONFIG.set('metadata:ows', 'contact_email', '${metadata:contact_email}')
    CONFIG.set('metadata:ows', 'contact_url', '${metadata:contact_url}')
    CONFIG.set('metadata:ows', 'contact_role', '${metadata:contact_role}')

    # OAPI metadata
    CONFIG.add_section('metadata:oapi')
    CONFIG.set('metadata:oapi', 'openapi', '3.0.2')
    CONFIG.set('metadata:oapi', 'title', 'Processes OGC API')
    CONFIG.set('metadata:oapi', 'description',
               'Implementation of processes api standards from the Open Geospatial Consortium.')
    CONFIG.set('metadata:oapi', 'terms_of_service', '')
    CONFIG.set('metadata:oapi', 'contact_name', '${metadata:contact_name}')
    CONFIG.set('metadata:oapi', 'contact_address', '${metadata:contact_address}')
    CONFIG.set('metadata:oapi', 'contact_email', '${metadata:contact_email}')
    CONFIG.set('metadata:oapi', 'contact_url', '${metadata:contact_url}')
    CONFIG.set('metadata:oapi', 'licence_name', '${metadata:licence_name}')
    CONFIG.set('metadata:oapi', 'licence_url', '${metadata:licence_url}')
    CONFIG.set('metadata:oapi', 'contact_role', '${metadata:contact_role}')
    CONFIG.set('metadata:oapi', 'external_doc_description', 'Py-qgis-wps server documentation')
    CONFIG.set('metadata:oapi', 'external_doc_url', 'https://docs.3liz.org/py-qgis-wps/')

    #
    # Used at runtime to set contextual configuration
    #
    CONFIG.add_section('wps.request')


def warn_unsafe_options():
    if CONFIG.getboolean('processing', 'unsafe.raw_destination_input_sink'):
        _log('********************************************')
        _log('* WARNING: !!! UNSAFE OPTION ACTIVATED !!! *')
        _log('********************************************')


def read_config_dict(userdict):
    """ Read configuration from dictionary

        Will override previous settings
    """
    CONFIG.read_dict(userdict)


def write_config(fh):
    """ Dump configuration to file
    """
    CONFIG.write(fh)


def read_config_file(cfgfile):
    """ Read configuration from file
    """
    cfgfile = os.path.abspath(cfgfile)
    with open(cfgfile) as fp:
        CONFIG.read_file(fp)
    _log(f'Configuration file <{cfgfile}> loaded')


def config_to_dict():
    """ Convert actual configuration to dictionary
    """
    def _items(p):
        for k in p.keys():
            try:
                yield k, p[k]
            except configparser.InterpolationMissingOptionError:
                yield k, p.get(k, raw=True)

    return {s: dict(_items(p)) for s, p in CONFIG.items()}


def validate_config_path(confname, confid, optional=False):
    """ Validate directory path
    """
    confvalue = CONFIG.get(confname, confid, fallback='')

    if not confvalue and optional:
        return

    confvalue = os.path.normpath(confvalue)
    if not os.path.isdir(confvalue):
        _log(f'ERROR: server->{confid} configuration value {confvalue} is not directory')
        raise ValueError(confvalue)

    if not os.path.isabs(confvalue):
        _log(f'ERROR: server->{confid} configuration value {confvalue} is not absolute path')
        raise ValueError(confvalue)

    CONFIG.set(confname, confid, confvalue)


def get_size_bytes(size):
    """Get real size of given obeject

    """
    size = size.lower()

    import re

    units = re.compile(r"[gmkb].*")
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

NO_DEFAULT = object()

# Chars that are to be replaced in env variable name
ENV_REPLACE_CHARS = ':.-@#$%&*'


@componentmanager.register_factory('@3liz.org/config-service;1')
class ConfigService:
    """ Act as a proxy
    """

    def __init__(self):
        self.allow_env = True

    def __get_impl(self, _get_fun, section: str, option: str, fallback: Any = NO_DEFAULT) -> Any:
        """
        """
        value = _get_fun(section, option, fallback=NO_DEFAULT)
        if value is NO_DEFAULT:
            # Look in environment
            # Note that the section must exists
            if self.allow_env:
                varname = f'QGSWPS_{section.upper()}_{option.upper()}'
                varname = functools.reduce(lambda s, c: s.replace(c, '_'), ENV_REPLACE_CHARS, varname)
                varvalue = os.getenv(varname)
                if varvalue is not None:
                    CONFIG.set(section, option, varvalue)
                # Let config parser translate the value for us
                value = _get_fun(section, option, fallback=fallback)
            else:
                value = fallback
        if value is NO_DEFAULT:
            raise KeyError(f'[{section}] {option}')
        return value

    get = functools.partialmethod(__get_impl, CONFIG.get)
    getint = functools.partialmethod(__get_impl, CONFIG.getint)
    getboolean = functools.partialmethod(__get_impl, CONFIG.getboolean)
    getfloat = functools.partialmethod(__get_impl, CONFIG.getfloat)

    def items(self, section):
        return CONFIG.items(section)

    def __getitem__(self, section):
        return CONFIG[section]

    def __contains__(self, section):
        return section in CONFIG

    def set(self, section: str, option: str, value: Any):
        CONFIG.set(section, option, value)

    def add_section(self, sectionname: str):
        # We do not care if the section already exists
        try:
            CONFIG.add_section(sectionname)
        except configparser.DuplicateSectionError:
            pass


confservice = ConfigService()
