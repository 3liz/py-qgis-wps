# QYWPS 

QYWPS is an implementation of the Web Processing Service standard from
the Open Geospatial Consortium. QWPS is written in Python.

QYWPS is a fork of PyWPS 

Requirements and limitations:

- Python 3.5+ only
- Windows not officially supported

# License

As of QWPS 4.0.0, QWPS is released under an
[MIT](https://en.wikipedia.org/wiki/MIT_License) license
(see [LICENSE.txt](LICENSE.txt)).

# Why QYWPS ?

PyWPS is a great piece of software but has some limitations that we need no overcome ta make it suitable
for our environment:

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

All these changes where not easy to implement without some drastic changes of the original code and it was
a matter of time so that we couldn't afford to go through the whole process of pull request submission.

That is, we have decided to fork the original project and go along with it. 

So, we are really grateful to the original authors of PyWPS for the nice piece of software that helped us very much
to start quickly our own project.   

## Why moving to Tornado instead WSGI

* We need to support asyncio: asyncio require a blocking running loop. This cannot be achieved simply in a WSGI architecture.
* Tornado has a better and better integration with native python asyncio and provide a great framework for handling server.

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
pip install QYWPS-X.Y.Z.tar.gz
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
usage: wpsserver [-h] [--logging {debug,info,warning,error}] [-c [PATH]]
                 [--version] [-p PORT] [-b IP] [-w NUM] [-u SETUID]
                 [--chdir DIR]

WPS server

optional arguments:
  -h, --help            show this help message and exit
  --logging {debug,info,warning,error}
                        set log level
  -c [PATH], --config [PATH]
                        Configuration file
  --version             Return version number and exit
  -p PORT, --port PORT  http port
  -b IP, --bind IP      Interface to bind to
  -w NUM, --workers NUM
                        Num workers
  -u SETUID, --setuid SETUID
                        uid to switch to
  --chdir DIR           Set the Working directory
```

## Configuration

### From config ini file

By default the wps server is not using any config file, but one can be used with the `--config` option.
A config file is a simple ini file, a sample config file is given with the sources.

### From environment variables

The server can be configured with environnement variables:

Confguration is done with environment variables:

- QYWPS\_SERVER\_WORKDIR: set the current dir processes, all processes will be running in that directory.
- QYWPS\_SERVER\_HOST\_PROXY: When the service is behind a reverse proxy, set this to the proxy entrypoint.
- QYWPS\_SERVER\_PARALLELPROCESSES: Number of parrallel process workers 
- QYWPS\_SERVER\_RESPONSE\_TIMEOUT: The max response time before killing a process.
- QYWPS\_SERVER\_RESPONSE\_EXPIRATION: The maxe time (in seconds) the response from a WPS process will be available.
- QYWPS\_SERVER\_WMS\_SERVICE\_URL: The base url for WMS service. Default to <hosturl>/wms. Responses from processing will
be retourned as WMS urls. This configuration variable set the base url for accessing results.
- QYWPS\_SERVER\_RESULTS\_MAP\_URI

### Logging

- QYWPS\_LOGLEVEL: the log level, should be `INFO` in production mode, `DEBUG` for debug output. 

### REDIS logstorage configuration

- QYWPS\_REDIS\_HOST: The redis host
- QYWPS\_REDIS\_PORT: The redis port. Default to 6379
- QYWPS\_REDIS\_DBNUM: The redis database number used. Default to 0


### Qgis project Cache configuration

- QYWPS\_CACHE\_ROOTDIR: Absolute path to the qgis projects root directory, projects referenges with the MAP parameter will be searched at this location

### Processing configuration

- QYWPS\_PROCESSSING\_PROVIDERS: List of providers for publishing algorithms (comma separated)
- QYWPS\_PROCESSSING\_PROVIDERS\_MODULE\_PATH: Path to look for processing algoritms provider to publish, algorithms from providers specified heres will be runnable as WPS processes.

# Configuring providers

A start, the service will look for a python file `__algorithms__.py`, the file must import providers that will be loaded into Qgis processing by the service. Published providers are a subset of those loaded.

The file `__algorithms__.py` must define a `providers` iterable that return the list of provider class (not instance !) to load.

Example:

```

from TestAlgorithmProvider1 import  AlgorithmProvider1
from TestAlgorithmProvider2 import  AlgorithmProvider2

# Define the provider's list
providers = ( AlgorithmProvider1, AlgorithmProvider2 )
```
 


