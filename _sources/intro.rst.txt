.. highlight:: python

.. _server_description:

Description
===========

Py-QGIS-WPS is an implementation of the [Web Processing Service](https://www.ogc.org/standards/wps)
standard from the Open Geospatial Consortium based on the QGIS Processing API.

It also implements the [processes OGC REST api](https://ogcapi.ogc.org/processes/)

This implementation allows you to expose and run on a server:
* QGISQGIS Processing algorithms available on Desktop
* QGIS Processing models and scripts
* QGIS plugins having a Processing provider according to their `metadata.txt` file

It's is written in Python and is a fork of [PyWPS](https://pywps.org/).

.. _server_requirements:

Requirements and limitations
----------------------------

- Python 3.7+ only
- Windows not officially supported
- Redis server

Any WPS client should work with this implementation. For instance QGIS Processing algorithms are available
in a web interface using [Lizmap WPS module](https://github.com/3liz/lizmap-wps-web-client-module).

.. _server_features:

Features
--------

- Asynchronous requests and parellel tasks execution
- Execution timeout
- Data expiration
- Status API.

.. _server_installation:

Installation
============

.. _server_source_install:

Install from source
-------------------

* Install from sources::

    pip install -e .

* Install from build version X.Y.Z::

    make dist
    pip install py-qgis-server-X.Y.Z.tar.gz


.. _server_running:


Running the server
==================

The server does not run as a daemon by itself, there is several way to run a command as a daemon.

For example:

* Use `Supervisor <http://supervisord.org/>`_. Will gives you full control over logs and server status notifications.
* Use the ``daemon`` command.
* Use systemd
* ...

Synopsis
--------

**pyqgiswps** [*options*]


Options
-------

.. program: pyqgiswps

.. option:: -d, --debug

    Force debug mode. This is the same as setting the :ref:`LOGGING_LEVEL <LOGGING_LEVEL>` option to ``DEBUG`` 
   
.. option:: -c, --config path

    Use the configuration file located at ``path``

.. option:: --dump-config

    Dump the configuration and exit



.. _server_docker_running:

Running with Docker
-------------------

Docker image is available on `docker-hub <https://hub.docker.com/r/3liz/qgis-wps>`_. 

All options are passed with environment variables. See the :ref:`Configuration settings <configuration_settings>`
for a description of the options.


Requests to OWS services
------------------------

The OWS requests use the following format:  ``/ows/?<ows_query_params>``

Example:

.. code-block:: text

    http://localhost:8080/ows/?SERVICE=WPS&VERSION=1.0.0&REQUEST=GetCapabilities




