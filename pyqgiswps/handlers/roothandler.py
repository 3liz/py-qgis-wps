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

class RootHandler(BaseHandler):
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
    

