#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import tornado

from .basehandler import BaseHandler
from ..version import __version__
from ..config import config_to_dict

class ServerInfosHandler(BaseHandler):
    def get(self):
        try:
            from qgis.core import Qgis
            from processing.core.Processing import RenderingStyles
            QGIS_VERSION="{} ({})".format(Qgis.QGIS_VERSION_INT,Qgis.QGIS_RELEASE_NAME)
            styles = RenderingStyles.styles
        except ImportError:
            QGIS_VERSION="n/a"
            styles = {}
            pass

        response = dict(tornado_ver=tornado.version,
                        version = __version__,
                        author="3Liz",
                        author_url="http://3liz.com",
                        qgis_version=QGIS_VERSION,
                        styles=styles,
                        config=config_to_dict())

        self.write_json(response)

    def head(self):
        from qgis.core import Qgis
        QGIS_VERSION="{} ({})".format(Qgis.QGIS_VERSION_INT,Qgis.QGIS_RELEASE_NAME)
        
        self.set_header("X-Qgis-version", QGIS_VERSION)


class LandingPageHandler(BaseHandler):
    """ Landing page 
    """
    def get(self):
        root = self.proxy_url()
        doc = {
            'title': "OGC processes API services for Qgis Processing",
            'page-type': "web-api-overview",
            'tags': [
                'API',
                'Reference',
                'Landing',
                'Qgis',
                'Qgis Processing',
                'Experimental',
            ],
            "links": [
                {
                    'href': f'{root}',
                    'rel': 'self',
                    'type': 'application/json',
                    'title': 'This document'
                },
                {
                    'href': f'{root}conformance',
                    'rel': 'http://www.opengis.net/def/rel/ogc/1.0/conformance',
                    'type': 'application/json',
                    'title': 'OGC API - Processes conformance classes implemented by this server'
                },
                {
                    'href': f'{root}processes',
                    'rel': 'http://www.opengis.net/def/rel/ogc/1.0/processes',
                    'type': 'application/json',
                    'title': 'Metadata about the processes'
                },
                {
                    'href': f'{root}jobs',
                    'type': 'application/json',
                    'rel': 'http://www.opengis.net/def/rel/ogc/1.0/job-list',
                    'title': 'The endpoint for job monitoring'
                },
                {
                    'href': f'{root}jobs.html',
                    'type': 'text/html',
                    'rel': 'http://www.opengis.net/def/rel/ogc/1.0/job-list',
                    'title': 'The endpoint for job monitoring as HTML'
                },
            ],
        }

        self.write_json(doc)
