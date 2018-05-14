# ============================================
# Backport some owslib pieces and bits for python 3
#
# Author: David Marteau <dmarteau@3liz.com>
# Original author: Tom Kralidis <tomkralidis@gmail.com>
# ===========================================

import logging

from .crs import Crs

#default namespace for nspath is OWS common
OWS_NAMESPACE = 'http://www.opengis.net/ows/1.1'

def nspath(path, ns=OWS_NAMESPACE):

    """
    Prefix the given path with the given namespace identifier.

    Parameters
    ----------
    - path: ElementTree API Compatible path expression
    - ns: the XML namespace URI.
    """

    if ns is None or path is None:
        return -1

    components = []
    for component in path.split('/'):
        if component != '*':
            component = '{%s}%s' % (ns, component)
        components.append(component)

    return '/'.join(components)


def testXMLValue(val, attrib=False):
    """
    Test that the XML value exists, return val.text, else return None
    Parameters
    ----------
    - val: the value to be tested
    """

    if val is not None:
        if attrib:
            return val.strip()
        elif val.text:  
            return val.text.strip()
        else:
            return None	
    else:
        return None


class BoundingBox(object):
    """Initialize an OWS BoundingBox construct"""
    def __init__(self, elem, namespace=OWS_NAMESPACE): 
        self.minx = None
        self.miny = None
        self.maxx = None
        self.maxy = None

        val = elem.attrib.get('crs')
        try:
            self.crs = Crs(val)
        except (AttributeError, ValueError):
            logging.warn('Invalid CRS %r. Expected integer')
            self.crs = None

        val = elem.attrib.get('dimensions')
        if val is not None:
            self.dimensions = int(testXMLValue(val, True))
        else:  # assume 2
            self.dimensions = 2

        val = elem.find(nspath('LowerCorner', namespace))
        tmp = testXMLValue(val)
        if tmp is not None:
            xy = tmp.split()
            if len(xy) > 1:
                if self.crs is not None and self.crs.axisorder == 'yx':
                    self.minx, self.miny = xy[1], xy[0] 
                else:
                    self.minx, self.miny = xy[0], xy[1]

        val = elem.find(nspath('UpperCorner', namespace))
        tmp = testXMLValue(val)
        if tmp is not None:
            xy = tmp.split()
            if len(xy) > 1:
                if self.crs is not None and self.crs.axisorder == 'yx':
                    self.maxx, self.maxy = xy[1], xy[0]
                else:
                    self.maxx, self.maxy = xy[0], xy[1]


