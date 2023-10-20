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
#
"""Validator classes are used for ComplexInputs, to validate the content
"""

import logging

from pyqgiswps.validator.mode import MODE
from pyqgiswps.validator.formats import FORMATS
import mimetypes
import os

LOGGER = logging.getLogger('SRVLOG')


def validategml(data_input, mode):
    """GML validation function

    :param data_input: :class:`ComplexInput`
    :param pyqgiswps.validator.mode.MODE mode:

    This function validates GML input based on given validation mode. Following
    happens, if `mode` parameter is given:

    `MODE.NONE`
        it will return always `True`
    `MODE.SIMPLE`
        the mimetype will be checked
    `MODE.STRICT`
        `GDAL/OGR <http://gdal.org/>`_ is used for getting the propper format.
    `MODE.VERYSTRICT`
        the :class:`lxml.etree` is used along with given input `schema` and the
        GML file is properly validated against given schema.
    """

    LOGGER.info('validating GML; Mode: %s', mode)
    passed = False

    if mode >= MODE.NONE:
        passed = True

    if mode >= MODE.SIMPLE:

        name = data_input.file
        (mtype, encoding) = mimetypes.guess_type(name, strict=False)
        passed = data_input.data_format.mime_type in {mtype, FORMATS.GML.mime_type}

    if mode >= MODE.STRICT:

        from pyqgiswps.dependencies import ogr
        data_source = ogr.Open(data_input.file)
        if data_source:
            passed = (data_source.GetDriver().GetName() == "GML")
        else:
            passed = False

    if mode >= MODE.VERYSTRICT:

        from lxml import etree
        from urllib.request import urlopen

        try:
            schema_url = data_input.data_format.schema
            gmlschema_doc = etree.parse(urlopen(schema_url))
            gmlschema = etree.XMLSchema(gmlschema_doc)
            passed = gmlschema.validate(etree.parse(data_input.stream))
        except Exception as e:
            LOGGER.warning(e)
            passed = False

    return passed


def validategeojson(data_input, mode):
    """GeoJSON validation example

    >>> import StringIO
    >>> class FakeInput(object):
    ...     json = open('point.geojson','w')
    ...     json.write('''{"type":"Feature", "properties":{}, "geometry":{"type":"Point", "coordinates":[8.5781228542328, 22.87500500679]}, "crs":{"type":"name", "properties":{"name":"urn:ogc:def:crs:OGC:1.3:CRS84"}}}''')  # noqa
    ...     json.close()
    ...     file = 'point.geojson'
    >>> class fake_data_format(object):
    ...     mimetype = 'application/geojson'
    >>> fake_input = FakeInput()
    >>> fake_input.data_format = fake_data_format()
    >>> validategeojson(fake_input, MODE.SIMPLE)
    True
    """

    LOGGER.info('validating GeoJSON; Mode: %s', mode)
    passed = False

    if mode >= MODE.NONE:
        passed = True

    """
    #
    # This is broken in many ways:
    # * Using deprecated jsonschema validation methods
    # * Segmentation fault when trying to validate in 
    #   VERY_STRICT mode.
    #
    if mode >= MODE.SIMPLE:

        name = data_input.file
        (mtype, encoding) = mimetypes.guess_type(name, strict=False)
        passed = data_input.data_format.mime_type in {mtype, FORMATS.GEOJSON.mime_type}

    if mode >= MODE.STRICT:

        from pyqgiswps.dependencies import ogr
        data_source = ogr.Open(data_input.file)
        if data_source:
           passed = (data_source.GetDriver().GetName() == "GeoJSON")
        else:
           passed = False

    # if mode >= MODE.VERYSTRICT:

        # import jsonschema
        f rom jsonschema.referencing import (
            Registry,
            DRAFT4,
        )
        import json

        # this code comes from
        # https://github.com/om-henners/GeoJSON_Validation/blob/master/geojsonvalidation/geojson_validation.py
        schema_home = os.path.join(_get_schemas_home(), "geojson")
        base_schema = os.path.join(schema_home, "geojson.json")

        with open(base_schema) as fh:
            geojson_base = json.load(fh)

        with open(os.path.join(schema_home, "crs.json")) as fh:
            crs_json = json.load(fh)

        with open(os.path.join(schema_home, "bbox.json")) as fh:
            bbox_json = json.load(fh)

        with open(os.path.join(schema_home, "geometry.json")) as fh:
            geometry_json = json.load(fh)

        cached_json = {
            "http://json-schema.org/geojson/crs.json": crs_json,
            "http://json-schema.org/geojson/bbox.json": bbox_json,
            "http://json-schema.org/geojson/geometry.json": geometry_json
        }

        resolver = jsonschema.RefResolver(
            "http://json-schema.org/geojson/geojson.json",
            geojson_base, store=cached_json
        )
        registry = Registry().with_resource(
            "http://json-schema.org/geojson/geojson.json",


        validator = jsonschema.Draft4Validator(geojson_base, resolver=resolver)
        try:
            validator.validate(json.loads(data_input.stream.read()))
            passed = True
        except jsonschema.ValidationError:
            passed = False
    """
    return passed


def validateshapefile(data_input, mode):
    """ESRI Shapefile validation example

    """

    LOGGER.info('validating Shapefile; Mode: %s', mode)
    passed = False

    if mode >= MODE.NONE:
        passed = True

    if mode >= MODE.SIMPLE:

        name = data_input.file
        (mtype, encoding) = mimetypes.guess_type(name, strict=False)
        passed = data_input.data_format.mime_type in {mtype, FORMATS.SHP.mime_type}

    if mode >= MODE.STRICT:

        from pyqgiswps.dependencies import ogr

        import zipfile
        z = zipfile.ZipFile(data_input.file)
        shape_name = None
        for name in z.namelist():
            z.extract(name, data_input.tempdir)
            if os.path.splitext(name)[1].lower() == '.shp':
                shape_name = name

        if shape_name:
            data_source = ogr.Open(os.path.join(data_input.tempdir, shape_name))

        if data_source:
            passed = (data_source.GetDriver().GetName() == "ESRI Shapefile")
        else:
            passed = False

    return passed


def validategeotiff(data_input, mode):
    """GeoTIFF validation example
    """

    LOGGER.info('Validating Shapefile; Mode: %s', mode)
    passed = False

    if mode >= MODE.NONE:
        passed = True

    if mode >= MODE.SIMPLE:

        name = data_input.file
        (mtype, encoding) = mimetypes.guess_type(name, strict=False)
        passed = data_input.data_format.mime_type in {mtype, FORMATS.GEOTIFF.mime_type}

    if mode >= MODE.STRICT:

        from pyqgiswps.dependencies import gdal
        data_source = gdal.Open(data_input.file)
        if data_source:
            passed = (data_source.GetDriver().ShortName == "GTiff")
        else:
            passed = False

    return passed


def _get_schemas_home():
    """Get path to schemas directory
    """
    schema_dir = os.path.join(
        os.path.abspath(
            os.path.dirname(__file__)
        ),
        os.path.pardir,
        "schemas")
    LOGGER.debug('Schemas directory: %s', schema_dir)
    return schema_dir


if __name__ == "__main__":
    import doctest
    from pyqgiswps.tests import temp_dir
    with temp_dir() as tmp:
        os.chdir(tmp)
        doctest.testmod()
