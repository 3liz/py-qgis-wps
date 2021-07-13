.. _qgis_styles:

Styling output layers
=======================

Py-qgis-wps use the ``RenderingStyle`` manager defined in ``processing.gui.RenderingStyle``.

The basic way to define styles for layer outputs is to define a ``styles.json`` files at each provider's
root directory that associate output to a ``.qml`` file applied to the output layer

Structure of ``styles.json`` file::

    {
        "algid": {
            "OUTPUT_NAME": "mystyle.qml"
        }
    }


The style defined in ``mystyle.qml`` will be applied to the output layer defined with ``OUTPUT_NAME``



