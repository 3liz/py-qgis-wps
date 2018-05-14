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

* Handle all request in asynchronous way: all jobs should run in a non blocking way
* Use multiprocessing Pool instead instanciating a new process each time.
* Uniforme Logging with the 'logging' module
* Serve response status
* Support python3 asyncio (and thus drop python2 supports)
* Support alternative 'Log' module like Redis which is more suited for scalability.
* Support streamed/chunked requests 
* Add extensions to WPS: TIMEOUT and EXPIRE

All these changes where not easy to implement without some drastic changes of the original code and it was
a matter of time so that we couldn't afford to go through the wall process of pull request submission.

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


