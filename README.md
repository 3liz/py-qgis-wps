# Py-Qgis-WPS 

Py-Qgis-WPS is an implementation of the Web Processing Service standard from
the Open Geospatial Consortium based on the Qgis processing API.

Py-Qgis-WPS will enable you to use Qgis processing algorithms written for Qgis desktop directy on server side.

Py-Qgis-WPS is written in Python.

Py-Qgis-WPS is a fork of PyWPS 

Requirements and limitations:

- Python 3.5+ only
- Windows not officially supported

# Why Py-Qgis-WPS ?

Py-Qgis-WPS differs from PyWPS in the following: 

* Qgis centric
* Handle all request in asynchronous way: all jobs should run in a non blocking way,  even
  with `storeExecuteResponse=true`
* Use multiprocessing Pool to handle task queue instead instanciating a new process each time.
* Uniform Logging with the 'logging' module
* Serve response status
* Support python3 asyncio (and thus drop python2 supports)
* Support alternative 'Log' module like Redis which is more suited for scalability.
* Support streamed/chunked requests 
* Add extensions to WPS: TIMEOUT and EXPIRE
* Drop MS Windows specifics
* Drop Python 2 support

All these changes where not easy to implement without some drastic changes of the original code and we think that it  deviates too much from the PyWPS original intentions. 

That is, we have decided to fork the original project and go along with it. 

So, we are really grateful to the original authors of PyWPS for the nice piece of software that helped us very much
to start quickly this project.   

## Why moving to Tornado instead WSGI

* We need to support asyncio: asyncio require a blocking running loop. This cannot be achieved simply in a WSGI architecture.
* Tornado has a better and better integration with native python asyncio and provide a great framework for developpingf http server.

## Extensions to WPS

### TIMEOUT extension

Specify the timeout for a process: if the process takes more than TIMEOUT seconds to run, the worker is then killed and an 
error status is retourned.

Set the the `TIMEOUT=<seconds>` in  GET requests. 

In POST requests, set the `timeout=<seconds>` attribut in the `<ResponseDocument>` tag

The server may configure maximum timeout value.


### EXPIRE extension

Specify the expiration time for stored results: after EXPIRE seconds after end of the wps process, all results will be
flushed from disks and local cache. Trying to requests the results again will return a 404 HTTP  error.

Set the the `EXPIRE=<seconds>` in  GET requests. 

In POST requests, set the `expire=<seconds>` attribut int the `<ResponseDocument>` tag

The server may configure maximum expiration value.


### status API

The status REST api will return the list of the stored status for all running and terminated wps processes.

Exemple for returning all stored status:
```
http://localhost:8080/ows/status/?SERVICE=WPS
```

Exemple for returning status for one given process from its uuid:
```
http://localhost:8080/ows/status/<uuid>?SERVICE=WPS
```


# Dependencies

See [requirements.txt](requirements.txt) file


# Installation from python package

*ADVICE*: You should always install in a python virtualenv. If you want to use system packages, setup your environment
with the `--system-site-packages` option.

See the official documentation for how to setup a python virtualenv:  https://virtualenv.pypa.io/en/stable/.

## From source

Install in development mode
```
pip install -e .
```

## From python package archive

```
pip install py-qgis-wps-X.Y.Z.tar.gz
```

# Running the server

The server from a command line interface:

The server does not run as a daemon by itself, there is several way to run a command as a daemon.

For example:

* Use Supervisor http://supervisord.org/. Will gives you full control over logs and server status notifications.
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

By default the wps server is not using any config file, but one can be used with the `--config` option.
A config file is a simple ini file, a sample config file is given with the sources.

### From environment variables

The server can be configured with environnement variables:

Confguration is done with environment variables:

- QGSWPS\_SERVER\_WORKDIR: set the current dir processes, all processes will be running in that directory.
- QGSWPS\_SERVER\_HOST\_PROXY: When the service is behind a reverse proxy, set this to the proxy entrypoint.
- QGSWPS\_SERVER\_PARALLELPROCESSES: Number of parrallel process workers 
- QGSWPS\_SERVER\_RESPONSE\_TIMEOUT: The max response time before killing a process.
- QGSWPS\_SERVER\_RESPONSE\_EXPIRATION: The maxe time (in seconds) the response from a WPS process will be available.
- QGSWPS\_SERVER\_WMS\_SERVICE\_URL: The base url for WMS service. Default to <hosturl>/wms. Responses from processing will
be retourned as WMS urls. This configuration variable set the base url for accessing results.
- QGSWPS\_SERVER\_RESULTS\_MAP\_URI

### Logging

- QGSWPS\_LOGLEVEL: the log level, should be `INFO` in production mode, `DEBUG` for debug output. 

### REDIS logstorage configuration

- QGSWPS\_REDIS\_HOST: The redis host
- QGSWPS\_REDIS\_PORT: The redis port. Default to 6379
- QGSWPS\_REDIS\_DBNUM: The redis database number used. Default to 0


### Qgis project Cache configuration

- QGSWPS\_CACHE\_ROOTDIR: Absolute path to the qgis projects root directory, projects referenges with the MAP parameter will be searched at this location

### Processing configuration

- QGSWPS\_PROCESSSING\_PROVIDERS: List of providers for publishing algorithms (comma separated)
- QGSWPS\_PROCESSSING\_PROVIDERS\_MODULE\_PATH: Path to look for processing algoritms provider to publish, algorithms from providers specified heres will be runnable as WPS processes.

# Exposing algorithms as WPS services

*IMPORTANT CHANGES* 


Since 1.1 , the `__algorithms__.py` method for declaring providers is no longer supported.

Processing providers following the same rules as  Qgis regular plugin with a special factory entrypoint: `WPSClassFactory(iface)` in the `__init__.py` file.

### The `metadata.txt` file

As regular Qgis plugin, a metadata.txt file must be present with a special entry `wps=True` indicating that
the plugin is available as a WPS service provider.

### Registering providers

The `iface`  parameter is a instance of `WPSServerInterface` which provide a 
`registerProvider( provider: QgsAlgorithmProvider, expose: bool = True) -> Any` method.

Exposed providers as WPS services must be registered usin the `registerProvider` method

Example:

```
def WPSClassFactory(iface: WPSServerInterface) -> Any:

    from TestAlgorithmProvider1 import  AlgorithmProvider1
    from TestAlgorithmProvider2 import  AlgorithmProvider2

    iface.registerProvider( AlgorithmProvider1() )
    iface.registerProvider( AlgorithmProvider2() )

``` 


