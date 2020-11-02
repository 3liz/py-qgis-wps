.. _configuration_settings:

Configuration Settings
======================

Configuration can be done either by using a configuration file or with environnement variable.

Except stated otherwise, the rule for environnement variable names is ``QGSRV_<SECTION>_<KEY>`` all in uppercase.


Common Configuration Options
=============================





.. _SERVER_HTTP_PORT:

SERVER_HTTP_PORT
----------------

Port to listen to

:Type: int
:Default: 8080
:Section: server
:Key: port
:Env: QGSRV_SERVER_HTTP_PORT



.. _SERVER_INTERFACES:

SERVER_INTERFACES
-----------------

Interfaces to listen to


:Type: string
:Default: 0.0.0.0
:Section: server
:Key: interfaces
:Env: QGSRV_SERVER_INTERFACES



.. _SERVER_OUTPUTFILE_AS_REFERENCE:

SERVER_OUTPUTFILE_AS_REFERENCE
------------------------------

Select if output files are returned by reference for deferred download or in response body as 
complex output.


:Type: boolean
:Default: no
:Section: server
:Key: outputfile_as_reference
:Env: QGSRV_SERVER_OUTPUTFILE_AS_REFERENCE



.. _SERVER_MAXINPUTSIZE:

SERVER_MAXINPUTSIZE
-------------------

Max input file fetched as remote reference

:Type: size
:Default: 100m
:Section: server
:Key: maxinputsize
:Env: QGSRV_SERVER_MAXINPUTSIZE



.. _SERVER_MAXBUFFERSIZE:

SERVER_MAXBUFFERSIZE
--------------------

Max request buffer size.

:Type: size
:Default: 1m
:Section: server
:Key: maxbuffersize
:Env: QGSRV_SERVER_MAXBUFFERSIZE



.. _SERVER_WORKDIR:

SERVER_WORKDIR
--------------

Parent working directory where processes are executed. Eache processes will create
a working directiry for storing results files and logs. 
The default value use the `gettempdir()` function.


:Type: path
:Default: System defaults
:Section: server
:Key: workdir
:Env: QGSRV_SERVER_WORKDIR



.. _SERVER_PARALLELPROCESSES:

SERVER_PARALLELPROCESSES
------------------------

The number of parallel processes runninc `execute` requests. Extra processes will be queued.


:Type: int
:Default: 1
:Section: server
:Key: parallelprocesses
:Env: QGSRV_SERVER_PARALLELPROCESSES



.. _SERVER_PROCESSLIFECYCLE:

SERVER_PROCESSLIFECYCLE
-----------------------

Maximal number of executions that can run in the same worker before beeing recreating
the worker.


:Type: int
:Default: 1
:Section: server
:Key: processlifecycle
:Env: QGSRV_SERVER_PROCESSLIFECYCLE



.. _SERVER_MAXQUEUESIZE:

SERVER_MAXQUEUESIZE
-------------------

Maximal number of waiting tasks - extra tasks will return a 509 in synchronous execution.


:Type: int
:Default: 100
:Section: server
:Key: maxqueuesize
:Env: QGSRV_SERVER_MAXQUEUESIZE



.. _SERVER_RESPONSE_TIMEOUT:

SERVER_RESPONSE_TIMEOUT
-----------------------

Timeout for tasks execution in seconds. Task running longer that this time will be aborted and
a timeout error is retourned.


:Type: int
:Default: 1800
:Section: server
:Key: response_timeout
:Env: QGSRV_SERVER_RESPONSE_TIMEOUT



.. _SERVER_RESPONSE_EXPIRATION:

SERVER_RESPONSE_EXPIRATION
--------------------------

Response expiration in seconds. After that delay from the tasks's end, data (working directory and status)
for that task will be deleted.


:Type: int
:Default: 86400
:Section: server
:Key: response_expiration
:Env: QGSRV_SERVER_RESPONSE_EXPIRATION



.. _SERVER_WMS_SERVICE_URL:

SERVER_WMS_SERVICE_URL
----------------------

The url for the service used to retrieve results as WMS/WFS references.
Usually this will correspond to a Qgis server serving OWS services from results projects.



:Type: string
:Default: Request host url
:Section: server
:Key: wms_service_url
:Env: QGSRV_SERVER_WMS_SERVICE_URL



.. _SERVER_RESULTS_MAP_URI:

SERVER_RESULTS_MAP_URI
----------------------

Base uri used for the MAP argument in WMS/WFS response references.
Define a base URI to use for 'MAP' arguments in WMS/WFS responses, this uri may
corresponds to an 'alias in py-qgis-server <https://py-qgis-server.readthedocs.io/en/latest/schemes.html#scheme-aliases>' _.



:Type: string
:Default: wps_result_map_uri
:Section: server
:Key: wms_service_url
:Env: QGSRV_SERVER_RESULTS_MAP_URI



.. _LOGGING_LEVEL:

LOGGING_LEVEL
-------------

Set the logging level

:Type: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
:Default: DEBUG
:Section: logging
:Key: level
:Env: QGSRV_LOGGING_LEVEL



.. _REDIS_HOST:

REDIS_HOST
----------

Redis storage backend host


:Type: string
:Default: localhost
:Section: logstorage:redis
:Key: host
:Env: QGSRV_REDIS_HOST



.. _REDIS_PORT:

REDIS_PORT
----------

Redis storage backend port


:Type: string
:Default: 6379
:Section: logstorage:redis
:Key: port
:Env: QGSRV_REDIS_PORT



.. _REDIS_DBNUM:

REDIS_DBNUM
-----------

Redis storage backend database index


:Type: string
:Section: logstorage:redis
:Key: dbnum
:Env: QGSRV_REDIS_DBNUM



.. _REDIS_PREFIX:

REDIS_PREFIX
------------

Redis storage backend key prefix.


:Type: string
:Default: pyqgiswps
:Section: logstorage:redis
:Key: prefix
:Env: QGSRV_REDIS_PREFIX



.. _CACHE_SIZE:

CACHE_SIZE
----------

The maximal number of Qgis projects held in cache. The cache strategy is LRU.


:Type: int
:Default: 10
:Section: projects.cache
:Key: size
:Env: QGSRV_CACHE_SIZE



.. _CACHE_ROOTDIR:

CACHE_ROOTDIR
-------------

The directory location for Qgis project files.


:Type: path
:Section: projects.cache
:Key: rootdir
:Env: QGSRV_CACHE_ROOTDIR



.. _CACHE_STRICT_CHECK:

CACHE_STRICT_CHECK
------------------

Activate strict checking of project layers. When enabled, Qgis projects
with invalid layers will be dismissed and an 'Unprocessable Entity' (422) HTTP error
will be issued.


:Type: boolean
:Default: yes
:Section: projects.cache
:Key: strict_check
:Env: QGSRV_CACHE_STRICT_CHECK



.. _PROCESSING_PROVIDERS_MODULE_PATH:

PROCESSING_PROVIDERS_MODULE_PATH
--------------------------------

Path to Qgis processing providers modules

:Type: path
:Section: processing
:Key: providers_module_path
:Env: QGSRV_PROCESSING_PROVIDERS_MODULE_PATH



.. _PROCESSING_EXPOSED_PROVIDERS:

PROCESSING_EXPOSED_PROVIDERS
----------------------------

Path to Qgis processing providers modules

:Type: list
:Default: script,model
:Section: processing
:Key: exposed_providers
:Env: QGSRV_PROCESSING_EXPOSED_PROVIDERS



.. _PROCESSING_ACCESSPOLICY:

PROCESSING_ACCESSPOLICY
-----------------------

Path to the access policy configuration file

:Type: path
:Default: PROCESSING_PROVIDERS_MODULE_PATH/accesspolicy.yml
:Section: processing
:Key: accesspolicy
:Env: QGSRV_PROCESSING_ACCESSPOLICY


