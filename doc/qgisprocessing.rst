.. _qgis_processing:

Running QGIS processing
=======================

.. _layer_mapping:

WPS input/output layer mapping
------------------------------

With Qgis desktop , Qgis processing algorithms usually apply on a Qgis  source project and computed layers are displayed in the same context as the source project.

Py-qgis-wps works the same way: a qgis project will be used as a source of input layers.
The difference is that, when an algorithm runs, it creates a qgis project file associated to the current task and register computed layers to it.

The created project may be used as OWS source with Qgis Server. Output layers are returned as complex objects
holding a reference to a WMS/WFS uri that can be used directly with Qgis server. The uri template is configurable
using the ``server/wms_response_uri`` configuration setting.


.. _contextualized_params:

Contextualized input parameters
-------------------------------

Tasks parameters are contextualized using the `MAP` query param. If a `MAP` parameters is given when
doinc a `DescripProcess` requests, allowed values for input layers will be taken from the qgis source project
according the type of the input layers.

Qgis project (.qgs) files and project stored in Postgres databases are both supported.

The best practice is to always provide a `MAP` parameters and include the possible input layer in a qgs project. This way you
may connect whatever data source supported by qgis and use them as input data in a safe way.

If you need to pass data to your algorithm from client-side, prefer inputs file parameter and small payloads.



.. _exposing_algorithms:

Exposing processing algorithms
==============================

The processing provider modules are searched in the path given by the :ref:`PROCESSING_PROVIDERS_MODULE_PATH`
config variable.

Processing providers following the same rules as  Qgis regular plugin with a special factory entrypoint: ``WPSClassFactory(iface)`` in the ``__init__.py`` file.


The ``metadata.txt`` file
-------------------------

As regular QGIS plugin, a metadata.txt file must be present with a special entry ``wps=True`` indicating that
the plugin is available as a WPS service provider.

Registering providers
---------------------

The ``iface``  parameter is a instance of ``WPSServerInterface`` which provide a
``registerProvider( provider: QgsAlgorithmProvider, expose: bool = True) -> Any`` method.

Exposed providers as WPS services must be registered usin the ``registerProvider`` method.

Example::

    def WPSClassFactory(iface: WPSServerInterface) -> Any:

        from TestAlgorithmProvider1 import  AlgorithmProvider1
        from TestAlgorithmProvider2 import  AlgorithmProvider2

        iface.registerProvider( AlgorithmProvider1() )
        iface.registerProvider( AlgorithmProvider2() )


Using scripts and models
------------------------

``Py-qgis-wps`` works with scripts and models. First creates a ``models/`` and a ``scripts/`` directory 
in the folder given by the :ref:`PROCESSING_PROVIDERS_MODULE_PATH` option.

Your processing module directory should be something like::

    <PROCESSSING_PROVIDERS_MODULE_PATH>/ 
    |
    |- models/
    |    |
    |    \- <your `.model3` files here>
    |
    \- scripts/
         |
         \- <your `.py` scripts here>


Then simple drop your ``.model3`` in the ``models/`` folder and the  python scripts in the ``scripts/`` folder.  
After restarting the workers you should see the corresponding algorithms in the list of published WPS jobs. 

Controlling what is exposed
---------------------------

Processing algorithm with the flag `FlagHideFromToolbox <https://qgis.org/pyqgis/3.0/core/Processing/QgsProcessingAlgorithm.html#qgis.core.QgsProcessingAlgorithm.FlagHideFromToolbox>`_ set will not be exposed as WPS process.

Parameters with the flag `FlagHidden <https://qgis.org/pyqgis/3.2/core/Processing/QgsProcessingParameterDefinition.html#qgis.core.QgsProcessingParameterDefinition.FlagHidden>`_ set wont be exposed in a ``DescribeProcess`` request.


.. _expose_wps_output_with_py_qgis_server:

Publishing WPS results with py-qgis-server
------------------------------------------

The ``server/wms_response_uri`` configuration default to ``wps_results:``

`Py-qgis-server <https://github.com/3liz/py-qgis-server>`_ can access to the wps results by defining a 
`custom scheme alias <https://py-qgis-server.readthedocs.io/en/latest/schemes.html#scheme-aliases>`_. that links the wps data to the  wps server workdir configuration ``wms_response_uri``.

Example::

    # Py-qgis-wps configuration. 
    [server]
    workdir = /path/to/wps/results

    # Py-qgis-server configuration
    # Bind the scheme 'wps_results:' to the wps output directory
    [projects.schemes]
    wps_results = /path/to/wps/results 


.. _reloading_providers:

Reloading providers
-------------------

Providers may be reloaded gracefully using the :ref:`SERVER_RESTARTMON` option.          
This allow for updatings providers, models and scripts without interrupting the service.


