#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import os
import asyncio
import mimetypes
import logging

from tornado.web import HTTPError
from pathlib import Path
from urllib.parse import urljoin
from datetime import datetime

from .basehandler import BaseHandler
from ..exceptions import NoApplicableCode, InvalidParameterValue, OperationNotSupported

LOGGER = logging.getLogger('SRVLOG')

from qywps.executors.logstore import logstore

def _format_size( size ):
    for u in ['B','K','M','G']:
        if size < 1024.0:
            if size < 10.0:
                return "%.1f%s" % (size,u)
            else:
                return "%.f%s" % (size,u)
        size /= 1024.0
    return '%.fT' % size


class StoreShellMixIn():
    """ Store api implementation
    """
    async def ls( self, uuid ):
        """ List all files in workdir
        """
        path = os.path.join(self._workdir, uuid)
        if not os.path.isdir(path):
            raise HTTPError(404, reason="The resource does not exists")

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
            raise HTTPError(404,reason="Resource not found")

        # Check modification time
        stat  = os.stat(full_path)
        mtime = str(stat.st_mtime)

        if self.request.headers.get('If-None-Match') == mtime:
            self.set_header('Etag', mtime)
            self.set_status(304)
            return

        # Set headers
        content_type = mimetypes.types_map.get(os.path.splitext(full_path)[1]) or "application/octet-stream"
        self.set_header("Content-Type", content_type)       
        self.set_header("Etag", mtime)

        # Set aggresive browser caching since the resource
        # is not going to change
        self.set_header("Cache-Control", "max-age=" + str(86400))

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

    async def archive(self, uuid):
        """ Archive the result storage
        """
        # Note implemented
        raise HTTPError(501, reason="Sorry, the method is not implemented yet")  




class StoreHandler(BaseHandler, StoreShellMixIn):
    """ Handle store requests
    """
    def initialize(self, workdir, chunk_size=65536):
        super().initialize()
        self._chunk_size = chunk_size
        self._workdir    = workdir

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
        if not uuid:
            raise HTTPError(403)

        # Get the status for uuid
        wps_status = self.application.wpsservice.get_status(uuid)
        if wps_status is None:
            raise HTTPError(404, reason="The resource does not exists") 

        action = self.get_query_argument('action') 
        
        if action.lower() == 'archive':
            await self.archive(uuid)
        else:
            raise HTTPError(400, reason="Invalid action parameter '%s'" % action)


class DownloadHandler(BaseHandler, StoreShellMixIn):
    """ The safe store handler work in two time

        1. Return a tokenized set of  url with a limited ttl
        2. Handle the url by returning the appropriate ressource
    """
    def initialize(self, workdir, query=False,  chunk_size=65536, ttl=30):
        super().initialize()
        self._chunk_size = chunk_size
        self._workdir    = workdir
        self._query      = query
        self._ttl        = ttl

    def create_dnl_url(self, uuid, filename):
        """ Store the request and create a download url
        """
        token = logstore.set_json({
            'uuid': uuid,
            'filename': filename,
        }, self._ttl)

        proxy_url = self.proxy_url()
        now       = datetime.utcnow().timestamp()
        path      = "dnl/_/{}".format(token)
        self.write_json({
              'root': "/{}".format(path),
              'link': "{}{}".format(proxy_url,path),
              'expire_at': datetime.fromtimestamp(now+self._ttl).isoformat()+'Z',
            })

    def get_dnl_params(self, token):
        """ Retrieve the download parameters
        """
        params = logstore.get_json(token)
        if params is None:
            raise HTTPError(403)
        return params['uuid'],params['filename']

    async def get(self, uuid, resource):
       """ Handle GET request
       """
       if self._query:
           # Store the request and return 
           # the temporary url
           self.create_dnl_url(uuid, resource)    
       else:
           # Download
           uuid,filename = self.get_dnl_params(resource)
           await self.dnl( uuid, filename)

  


