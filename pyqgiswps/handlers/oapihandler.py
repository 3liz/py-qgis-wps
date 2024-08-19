#
# Copyright 2022 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import logging

from pathlib import Path
from typing import Optional

from ..config import confservice
from ..version import __version__
from .basehandler import BaseHandler, DownloadMixIn

LOGGER = logging.getLogger('SRVLOG')


class OpenApiHandler(BaseHandler, DownloadMixIn):
    """ Open api interface
    """

    def initialize(self, path: str):
        super().initialize()

        self._path = Path(path)
        self._metadata = confservice['metadata:oapi']

    async def get(self, resource: Optional[str] = None):
        """
        """
        if not resource:
            self._server = self.proxy_url()
            doc = self.oapi_root()
            doc.update(
                servers=[{
                    'url': self._server,
                }],
                info=self.oapi_info(),
                externalDocs=self.oapi_external_doc(),
                paths=self.oapi_paths(),
            )
            self.write_json(doc)
        else:
            resource = self._path.joinpath(resource)
            if resource.suffix in ('.yml', '.yaml'):
                content_type = 'text/plain; charset=utf-8'
            else:
                content_type = None
            await self.download(
                resource,
                content_type=content_type,
                cache_control="max-age=300",
            )

    def qgis_version_info(self):
        try:
            from qgis.core import Qgis
            qgis_version = Qgis.QGIS_VERSION_INT
            qgis_release = Qgis.QGIS_RELEASE_NAME
        except ImportError:
            LOGGER.critical("Failed to import Qgis module !")
            qgis_version = qgis_release = 'n/a'

        return (
            ('x-qgis-version', qgis_version),
            ('x-qgis-release', qgis_release),
        )

    def oapi_root(self):
        return {'openapi': self._metadata['openapi']}

    def oapi_info(self):
        _m = self._metadata.get
        doc = {
            'title': _m('title'),
            'description': _m('description'),
            'termsOfService': _m('terms_of_service'),
            'contact': {
                'name': _m('contact_name'),
                'url': _m('contact_url'),
                'email': _m('contact_email'),
            },
            'licence': {
                'name': _m('licence_name'),
                'url': _m('licence_url'),
            },
            'version': __version__,
        }

        doc.update(self.qgis_version_info())
        return doc

    def oapi_external_doc(self):
        return {
            'description': self._metadata['external_doc_description'],
            'url': self._metadata['external_doc_url'],
        }

    def oapi_paths(self):
        """  See
        """
        url = f"{self._server}api"

        def _ref(p):
            return {'$ref': f"{url}/{p}"}

        return {
            '/': _ref("landingpage.yml"),
            '/conformance': _ref("conformance.yml"),
            '/processes': _ref("processes.yml"),
            '/processes/{processID}': _ref("process_description.yml"),
            '/processes/{processID}/execution': _ref("./process_execute.yml"),
            '/jobs': _ref("jobs.yml"),
            '/jobs/{jobID}': _ref("job_status.yml"),
            '/jobs/{jobID}/results': _ref("job_results.yml"),
        }
