# Py-QGIS-WPS 

Py-QGIS-WPS is an implementation of the [Web Processing Service](https://www.ogc.org/standards/wps)
standard from the Open Geospatial Consortium based on the QGIS Processing API.

This implementation allows you to expose and run on a server:
* QGIS Processing algorithms available on Desktop
* QGIS Processing models and scripts
* QGIS plugins having a Processing provider according to their `metadata.txt`file

It is written in Python and is a fork of [PyWPS](https://pywps.org/).

Requirements and limitations :

- Python 3.5+ only
- Windows not officially supported
- Redis server 


# Documentation:

Latest documentation is available on [ReadTheDoc](https://py-qgis-wps.readthedocs.io/en/latest/index.html)

# Why Py-QGIS-WPS ?

Py-QGIS-WPS differs from [PyWPS](https://pywps.org/) in the following: 

* QGIS centric
* Handle all request in asynchronous way: all jobs should run in a non-blocking way, even
  with `storeExecuteResponse=true`
* Use multiprocessing Pool to handle task queue instead instantiating a new process each time.
* Uniform Logging with the 'logging' module
* Serve response statu
* Use Redis for asynchronous status storage.
* Support python3 asyncio (and thus drop python2 supports)
* Support streamed/chunked requests 
* Add extensions to WPS: TIMEOUT and EXPIRE
* Drop MS Windows specifics
* Drop Python 2 support

All these changes where not easy to implement without some drastic changes of the original code and we think
that it  deviates too much from the PyWPS original intentions.

That is, we have decided to fork the original project and go along with it. 

So, we are really grateful to the original authors of PyWPS for the nice piece of software that helped us very much
to start quickly this project.   

## Why moving to Tornado instead WSGI

* We need to support asyncio: asyncio requires a blocking running loop. This cannot be achieved simply in a WSGI architecture.
* Tornado has a better and better integration with native python asyncio and provide a great framework for developing a http server.

## Extensions to WPS

### TIMEOUT extension

Specify the timeout for a process: if the process takes more than TIMEOUT seconds to run, the worker is then killed and an 
error status is returned.

Set the the `TIMEOUT=<seconds>` in  GET requests. 

In POST requests, set the `timeout=<seconds>` attribut in the `<ResponseDocument>` tag.

The server may configure maximum timeout value.


### EXPIRE extension

Specify the expiration time for stored results: after EXPIRE seconds after the end of the wps process, all results will be
flushed from disks and local cache. Trying to request the results again will return a 404 HTTP  error.

Set the the `EXPIRE=<seconds>` in  GET requests. 

In POST requests, set the `expire=<seconds>` attribut int the `<ResponseDocument>` tag.

The server may configure maximum expiration value.


### Status API

The status REST api will return the list of the stored status for all running and terminated wps processes.

Example for returning all stored status:
```
http://localhost:8080/ows/status/?SERVICE=WPS
```

Example for returning status for one given process from its uuid:
```
http://localhost:8080/ows/status/<uuid>?SERVICE=WPS
```

# Running QGIS processing.

## WPS input/output layer mapping

With Qgis desktop , Qgis processing algorithms usually apply on a Qgis  source project and computed layers are displayed in the same context as the source project. 

Py-qgis-wps works the same way: a qgis project will be used as a source of input layers. 
The difference is that, when an algorithm runs, it creates a qgis project file associated to the current task and register computed layers to it.  

The created project may be used as OWS source with Qgis Server. Output layers are returned as complex objects
holding a reference to a WMS/WFS uri that can be used directly with Qgis server. The uri template is configurable 
using the `server/wms_response_uri` configuration setting.

## Contextualized input parameters

Tasks parameters are contextualized using the `MAP` query param. If a `MAP` parameters is given when
doing a `DescripProcess` requests, allowed values for input layers will be taken from the qgis source project
according the type of the input layers.  

Qgis project (.qgs) files and project stored in Postgres databases are both supported.

The best practice is to always provide a `MAP` parameters and include the possible input layer in a qgs project. This way you
may connect whatever data source supported by qgis and use them as input data in a safe way.

If you need to pass data to your algorithm from client-side, prefer inputs file parameter and small payloads.


# Dependencies

See [requirements.txt](requirements.txt) file.


# Installation from python package

*ADVICE*: You should always install in a python virtualenv. If you want to use system packages, setup your environment
with the `--system-site-packages` option.

See the official documentation for how to setup a python virtualenv:  https://virtualenv.pypa.io/en/stable/.

## From source

Install in development mode
```bash
pip install -e .
```

## From python package archive

```bash
pip install py-qgis-wps-X.Y.Z.tar.gz
```

# Running the server

The server from a command line interface:

The server does not run as a daemon by itself, there are several ways to run a command as a daemon.

For example:

* Use Supervisor http://supervisord.org/ will give you full control over logs and server status notifications.
* Use the `daemon` command.
* Use Docker

# Running the server

## Usage

```
usage: wpsserver [-h] [-d] [-c [PATH]]
                 [--version] [-p PORT] [-b IP] [-u SETUID]

WPS server

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           Set debug mode  
  -c [PATH], --config [PATH]
                        Configuration file
  --version             Return version number and exit
  -p PORT, --port PORT  http port
  -b IP, --bind IP      Interface to bind to
  -u SETUID, --setuid SETUID
                        uid to switch to
```

## Configuration

### From config ini file

By default, the wps server is not using any config file, but one can be used with the `--config` option.
A config file is a simple ini file, a sample config file is given with the sources.

### From environment variables

The server can be configured with environnement variables:

Configuration is done with environment variables:

- QGSWPS\_SERVER\_WORKDIR: set the current dir processes, all processes will be running in that directory.
- QGSWPS\_SERVER\_HOST\_PROXY: When the service is behind a reverse proxy, set this to the proxy entrypoint.
- QGSWPS\_SERVER\_PARALLELPROCESSES: Number of parallel process workers
- QGSWPS\_SERVER\_RESPONSE\_TIMEOUT: The max response time before killing a process.
- QGSWPS\_SERVER\_RESPONSE\_EXPIRATION: The max time (in seconds) the response from a WPS process will be available.
- QGSWPS\_SERVER\_WMS\_SERVICE\_URL: The base url for WMS service. Default to <hosturl>/wms. Responses from processing will
be retourned as WMS urls. This configuration variable set the base url for accessing results.
- QGSWPS\_SERVER\_RESULTS\_MAP\_URI

### Logging

- QGSWPS\_LOGLEVEL: the log level, should be `INFO` in production mode, `DEBUG` for debug output. 

### REDIS storage configuration

- QGSWPS\_REDIS\_HOST: The redis host
- QGSWPS\_REDIS\_PORT: The redis port. Default to 6379
- QGSWPS\_REDIS\_DBNUM: The redis database number used. Default to 0


### Qgis project Cache configuration

- QGSWPS\_CACHE\_ROOTDIR: Absolute path to the qgis projects root directory, projects referenced with the MAP parameter will be searched at this location

### Processing configuration

- QGSWPS\_PROCESSSING\_PROVIDERS\_MODULE\_PATH: Path to look for processing algorithms provider to publish, algorithms from providers specified here will be runnable as WPS processes.

# Exposing algorithms as WPS services

Note that since 1.1 , the `__algorithms__.py` method for declaring providers is no longer supported.

Processing providers following the same rules as  Qgis regular plugin with a special factory entrypoint: `WPSClassFactory(iface)` in the `__init__.py` file.

### The `metadata.txt` file

As regular QGIS plugin, a metadata.txt file must be present with a special entry `wps=True` indicating that
the plugin is available as a WPS service provider.

### Registering providers

The `iface`  parameter is a instance of `WPSServerInterface` which provide a 
`registerProvider( provider: QgsAlgorithmProvider, expose: bool = True) -> Any` method.

Exposed providers as WPS services must be registered using the `registerProvider` method

Example:

```python
def WPSClassFactory(iface: WPSServerInterface) -> Any:

    from TestAlgorithmProvider1 import  AlgorithmProvider1
    from TestAlgorithmProvider2 import  AlgorithmProvider2

    iface.registerProvider( AlgorithmProvider1() )
    iface.registerProvider( AlgorithmProvider2() )

``` 

## Controlling what is exposed:

Processing algorithm with the flag [FlagHideFromToolbox](https://qgis.org/pyqgis/3.0/core/Processing/QgsProcessingAlgorithm.html#qgis.core.QgsProcessingAlgorithm.FlagHideFromToolbox) set will not be exposed as WPS process.  

Parameters with the flag [FlagHidden](https://qgis.org/pyqgis/3.2/core/Processing/QgsProcessingParameterDefinition.html#qgis.core.QgsProcessingParameterDefinition.FlagHidden) set won't be exposed in a `DescribeProcess` request

# Références

* [OGC standards](https://www.ogc.org/standards)
* [Introduction to WPS](http://opengeospatial.github.io/e-learning/wps/text/basic-index.html)
* [Py-qgis-server at FOSS4G 2019](https://www.youtube.com/watch?v=YL1tdcJwimA).


