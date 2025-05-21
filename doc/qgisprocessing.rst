.. _qgis_processing:

Running QGIS processing
=======================

.. _layer_mapping:

WPS input/output layer mapping
------------------------------

With QGIS desktop , QGIS processing algorithms usually apply on a QGIS source project and computed layers are displayed in the same context as the source project.

Py-qgis-wps works the same way: a qgis project will be used as a source of input layers.
The difference is that, when an algorithm runs, it creates a qgis project file associated to the current task and register computed layers to it.

The created project may be used as OWS source with QGIS Server. Output layers are returned as complex objects
holding a reference to a WMS/WFS uri that can be used directly with QGIS server. The uri template is configurable
using the ``server/wms_response_uri`` configuration setting.


.. _contextualized_params:

Contextualized input parameters
-------------------------------

Tasks parameters are contextualized using the `MAP` query param. If a `MAP` parameters is given when
doing a `DescripProcess` requests, allowed values for input layers will be taken from the qgis source project
according the type of the input layers.

QGIS project (.qgs) files and project stored in Postgres databases are both supported.

The best practice is to always provide a `MAP` parameters and include the possible input layer in a qgs project. This way you
may connect whatever data source supported by qgis and use them as input data in a safe way.

If you need to pass data to your algorithm from client-side, prefer inputs file parameter and small payloads.



.. _exposing_algorithms:

Exposing processing algorithms
==============================

The processing provider modules are searched in the path given by the :ref:`PROCESSING_PROVIDERS_MODULE_PATH`
config variable.


Registering providers
---------------------

There is nothing special to do for using a Qgis plugin with |ProjectName|. 

As for Qgis desktop, |ProjectName| expect the a pluging to follow
the same rules as for any other plugins `implementing processing 
providers <https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/processing.html>`_`. 

As regular QGIS plugin, a metadata.txt file must be present with the variable
``hasProcessingProvider=yes`` indicating that the plugin is available as a processing 
service provider factory.

The object returned by the ``classFactory`` function must implement the ``initProcessing``
method.

.. note::

   The ``initProcessing`` method will be the one and only one method called by
   |ProjectName|.       

|ProjectName| use the same entrypoint a Qgis desktop plugin except that
not ``QgsInterface`` is provided.


.. warning::

    | The ``iface: QgsInterface`` parameter is used for initializing Gui component 
      of the plugin in Qgis desktop.  This parameter will be set to ``None`` when
      loaded from |ProjectName|.
    | Implementors should take care to check the value of the ``iface`` parameter
      and drop all gui initialization if not set.
    | The only thing to do is to register the providers the same way as for 
      using in Qgis Desktop.   


Example::

    from qgis.core import QgsApplication

    from .provider import TestAlgorithmProvider


    class Test:
        def __init__(self):
            pass

        def initProcessing(self):
            reg = QgsApplication.processingRegistry()

            # XXX we *MUST* keep instance of provider
            self._provider = TestAlgorithmProvider()
            reg.addProvider(self._provider)


    def classFactory(iface: QgsInterface|None) -> Test:
        if iface is not None:
            # Initialize GUI
            ... 

        return Test()



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
`custom scheme alias <https://docs.3liz.org/py-qgis-server/schemes.html#scheme-aliases>`_. that links the wps data to the  wps server workdir configuration ``wms_response_uri``.

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
This allow for updating providers, models and scripts without interrupting the service.
