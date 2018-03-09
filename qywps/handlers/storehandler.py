##################################################################
# Copyright 2018 3liz                                            #
# Author: David Marteau                                          #
#                                                                #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import os
import asyncio
import mimetypes
import logging

from pathlib import Path
from urllib.parse import urljoin

from .basehandler import BaseHandler
from ..exceptions import NoApplicableCode, InvalidParameterValue, OperationNotSupported

LOGGER = logging.getLogger("QYWPS")


def _format_size( size ):
    for u in ['B','K','M','G']:
        if size < 1024.0:
            if size < 10.0:
                return "%.1f%s" % (size,u)
            else:
                return "%.f%s" % (size,u)
        size /= 1024.0
    return '%.fT' % size



class StoreHandler(BaseHandler):
    """ Handle WPS requests
    """
    def initialize(self, workdir, chunk_size=65536):
        super().initialize()
        self._chunk_size = chunk_size
        self._workdir    = workdir

    def prepare(self):
        service = self.get_query_argument('service')
        if service.lower() != 'wps':
            raise InvalidParameterValue('parameter SERVICE [%s] not supported' % service, 'service')

    async def ls( self, uuid ):
        """ List all files in workdir
        """
        path = os.path.join(self._workdir, uuid)
        if not os.path.isdir(path):
            raise NoApplicableCode("The resource does not exists", code=404)

        proxy_url = self.proxy_url()
        store_url = self.application.config['store_url']

        def file_records(rootdir, dirs, files, rootfd):
            root = Path(rootdir)
            for file in files:
                stat  = os.stat(file, dir_fd=rootfd)
                name  = (root / file).relative_to(path).as_posix()
                yield {
                    'name': name,
                    'content_length': stat.st_size,
                    'store_url'     : store_url.format(host_url=proxy_url, uuid=uuid, file=name),
                    'display_size'  : _format_size(stat.st_size),
                }

        data = [f for args in os.fwalk(path) for f in file_records(*args)]
        self.write_json({ "files": data })                  

    async def dnl( self, uuid, filename):
        """ Return output file from process working dir
        """
        full_path  = os.path.join(self._workdir, uuid, filename)
        if not os.path.isfile(full_path):
            LOGGER.error("File '%s' not found", full_path)
            raise NoApplicableCode("The resource does not exists", code=404)

        # The resource is asked again, just tell that it is
        # not modified
        if self.request.headers.get("If-Modified-Since"):
            self.set_status(304)
            return

        if self.request.headers.get('If-None-Match') == uuid:
            self.set_header('Etag', uuid)
            self.set_status(304)
            return

        # Set headers
        content_type = mimetypes.types_map.get(os.path.splitext(full_path)[1]) or "application/octet-stream"
        self.set_header("Content-Type", content_type)       
        self.set_header("Etag", uuid)

        # Set aggresive browser caching since the resource
        # is not going to change
        self.set_header("Cache-Control", "max-age=" + str(86400*365*10))

        # Push data
        chunk_size = self._chunk_size
        with open(full_path,'rb') as fp:
            while True:
                chunk = fp.read(chunk_size)
                if chunk:
                    self.write(chunk)
                    await self.flush()
                else:
                    break

    async def get(self, uuid, filename=None):
        """ Handle GET request
        """
        if filename:
            await self.dnl( uuid, filename)
        else:
            await self.ls( uuid )


    async def post(self, uuid ):
        """ Handle POST actions
        """
        pass




