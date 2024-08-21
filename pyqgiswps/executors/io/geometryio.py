#
# Copyright 2020 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Handle geometry
"""
import json
import logging
import re

from typing import (
    Any,
    Dict,
    Optional,
    Union,
)

from osgeo import ogr

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterGeometry,
    QgsProcessingParameterPoint,
    QgsRectangle,
    QgsReferencedGeometry,
    QgsReferencedPointXY,
    QgsReferencedRectangle,
)

from pyqgiswps.app.common import Metadata
from pyqgiswps.exceptions import InvalidParameterValue, NoApplicableCode
from pyqgiswps.inout import (
    FORMATS,
    BoundingBoxInput,
    ComplexInput,
    Format,
    LiteralInput,
    WPSInput,
)

from ..processingcontext import MapContext, ProcessingContext

Geometry = Union[
    QgsGeometry,
    QgsReferencedGeometry,
    QgsReferencedPointXY,
]

LOGGER = logging.getLogger('SRVLOG')

GeometryParameterTypes = (QgsProcessingParameterPoint, QgsProcessingParameterGeometry)

if Qgis.QGIS_VERSION_INT >= 33000:
    # Geometry displaystring
    GeomTypeDisplayString = {
        Qgis.GeometryType.PointGeometry: 'Point',
        Qgis.GeometryType.LineGeometry: 'Line',
        Qgis.GeometryType.PolygonGeometry: 'Polygon',
        Qgis.GeometryType.NullGeometry: 'Null',
    }

    def GetGeomTypeDisplayString(geomtype):
        return GeomTypeDisplayString.get(geomtype, "Unknown")
else:
    from qgis.core import QgsWkbTypes

    def GetGeomTypeDisplayString(geomtype):
        return QgsWkbTypes.geometryDisplayString(geomtype)

# ------------------------------------
# Processing parameters ->  WPS input
# ------------------------------------


def parse_extent_input(
    param: QgsProcessingParameterDefinition,
    kwargs: Dict[str, Any],
    context: Optional[MapContext] = None,
) -> BoundingBoxInput:
    """ Convert extent processing input to bounding box input"
    """
    crsid = None
    if context:
        project = context.project()
        # Get the crs from the project
        # Return a QgsCoordinateReferenceSystem
        crs = project.crs()
        if crs and crs.isValid():
            crsid = crs.authid()

    if not crsid:
        # Default CRS
        crsid = 'EPSG:4326'

    # XXX This is the default, do not presume anything
    # about effective crs at compute time
    kwargs['crss'] = [crsid]
    return BoundingBoxInput(**kwargs)


def parse_input_definition(
    param: QgsProcessingParameterDefinition,
    kwargs: Dict[str, Any],
    context: Optional[MapContext] = None,
) -> WPSInput | None:
    """ Convert processing input to File Input
    """
    typ = param.type()

    if typ == 'crs':
        kwargs['data_type'] = 'string'
        return LiteralInput(**kwargs)
    elif typ == "extent":
        return parse_extent_input(param, kwargs, context)
    elif isinstance(param, GeometryParameterTypes):
        kwargs['supported_formats'] = [
            Format.from_definition(FORMATS.GEOJSON),
            Format.from_definition(FORMATS.GML),
            Format.from_definition(FORMATS.WKT),
        ]
        if isinstance(param, QgsProcessingParameterGeometry):
            # Add metadata from requiered geometryTypes
            kwargs['metadata'].extend(
                Metadata('processing:geometryType', GetGeomTypeDisplayString(geomtype))
                for geomtype in param.geometryTypes()
            )
            if param.allowMultipart():
                kwargs['metadata'].append(Metadata('processing:allowMultipart'))
        return ComplexInput(**kwargs)

    return None


# --------------------------------------
# WPS inputs ->  processing inputs data
# --------------------------------------

WKT_EXPR = re.compile(r"^\s*(?:(CRS|SRID)=(.*);)?(.*?)$")


def wkt_to_geometry(wkt: str) -> Geometry:
    """ Convert wkt to qgis geometry

        Handle CRS= prefix
    """
    m = WKT_EXPR.match(wkt)
    if m:
        g = QgsGeometry.fromWkt(m.groups('')[2])
        if not g.isNull():
            crs_str = m.groups('')[1]
            if m.groups('')[0] == 'SRID':
                crs_str = f'POSTGIS:{crs_str}'

            crs = QgsCoordinateReferenceSystem(crs_str)
            if crs.isValid():
                g = QgsReferencedGeometry(g, crs)
        return g
    raise InvalidParameterValue("Invalid wkt format")


def json_to_geometry(input_data: str) -> Geometry:
    """ Handle json to qgis geometry
    """
    try:
        data: Dict = json.loads(input_data)
        crs = data.get('crs')
        if crs:
            crs = QgsCoordinateReferenceSystem(crs['properties']['name'])
            data = data.get('geometry', data)
        geom = ogr.CreateGeometryFromJson(json.dumps(data))
        if geom:
            # XXX There is no method for direct import
            # from json
            geom = QgsGeometry.fromWkt(geom.ExportToWkt())
            if crs and crs.isValid():
                geom = QgsReferencedGeometry(geom, crs)
            return geom
    except (json.JSONDecodeError, KeyError) as err:
        LOGGER.error("Error decoding json input: %s", err)

    raise InvalidParameterValue("Invalid geojson format")


SRSNAME_EXPR = re.compile(r'\bsrsname\b="([^"]+)"', re.IGNORECASE)


def gml_to_geometry(gml: str) -> Geometry:
    """ Handle json to qgis geometry
    """
    # Lookup for srsName
    geom = ogr.CreateGeometryFromGML(gml)
    if not geom:
        raise InvalidParameterValue("Invalid gml format")

    geom = QgsGeometry.fromWkt(geom.ExportToWkt())
    # Check for crs
    m = SRSNAME_EXPR.search(gml)
    if m:
        crs = QgsCoordinateReferenceSystem(m.groups('')[0])
        if crs.isValid():
            geom = QgsReferencedGeometry(geom, crs)
    return geom


def input_to_geometry(inp: WPSInput) -> Geometry:
    """ Handle point from complex input
    """
    mime_type = inp.data_format.mime_type
    match mime_type:
        case FORMATS.WKT.mime_type:
            return wkt_to_geometry(inp.data)
        case FORMATS.GEOJSON.mime_type:
            return json_to_geometry(inp.data)
        case FORMATS.GML.mime_type:
            return gml_to_geometry(inp.data)

    raise NoApplicableCode(f"Unsupported data format: {inp.data_format}")


def input_to_point(inp: WPSInput) -> Geometry:
    """ Convert input to point
    """
    g = input_to_geometry(inp)
    if isinstance(g, QgsReferencedGeometry):
        g = QgsReferencedPointXY(g.centroid().asPoint(), g.crs())
    return g


def input_to_extent(inp: WPSInput) -> Geometry:
    """ Convert to extent
    """
    r = inp.data
    rect = QgsRectangle(r[0], r[1], r[2], r[3])
    ref = QgsCoordinateReferenceSystem(inp.crs)
    return QgsReferencedRectangle(rect, ref)


def get_processing_value(
    param: QgsProcessingParameterDefinition,
    inp: WPSInput,
    context: ProcessingContext,
) -> Geometry:
    """ Return processing value from wps inputs

        Processes other inputs than layers
    """
    typ = param.type()

    value: Geometry

    if isinstance(param, QgsProcessingParameterGeometry):
        value = input_to_geometry(inp[0])
    elif isinstance(param, QgsProcessingParameterPoint):
        value = input_to_point(inp[0])
    elif typ == 'extent':
        value = input_to_extent(inp[0])
    elif typ == 'crs':
        # XXX CRS may be expressed as EPSG (or QgsProperty ?)
        value == inp[0].data
    else:
        value = None

    return value
