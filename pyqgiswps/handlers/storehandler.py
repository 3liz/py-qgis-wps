#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import os
import mimetypes
import logging

from tornado.web import HTTPError
from pathlib import Path
from datetime import datetime

from pyqgiswps.executors.logstore import logstore

from .basehandler import BaseHandler

from typing import (
    Optional,
    Awaitable,
)

LOGGER = logging.getLogger('SRVLOG')


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

    # XXX DEPRECATED - will be removed at version 1.9
    def legacy_resource_list(self, path, uuid):
        # Legacy json schema for
        store_url = f"{self.proxy_url()}store/{uuid}/"

        def file_records(rootdir, dirs, files, rootfd):
            root = Path(rootdir)
            for file in files:
                stat  = os.stat(file, dir_fd=rootfd)
                name  = (root / file).relative_to(path).as_posix()
                yield {
                    'name': name,
                    'content_length': stat.st_size,
                    'store_url'     : store_url + name,
                    'display_size'  : _format_size(stat.st_size),
                }
        data = [f for args in os.fwalk(path) for f in file_records(*args)]
        content = { "files": data }       

        return content

    async def ls( self, uuid ):
        """ List all files in workdir
        """
        path = os.path.join(self._workdir, uuid)
        if not os.path.isdir(path):
            raise HTTPError(404, reason="The resource does not exists")


        if self._legacy:
            # XXX DEPRECATED - will be removed at version 1.9
            content = self.legacy_resource_list(path, uuid) 
        else:
            store_url = f"{self.proxy_url()}jobs/{uuid}/"
            # Open api conformant schema
            def file_records(rootdir, dirs, files, rootfd):
                root = Path(rootdir)
                for file in files:
                    stat  = os.stat(file, dir_fd=rootfd)
                    name  = (root / file).relative_to(path).as_posix()
                    content_type = mimetypes.types_map.get(
                        os.path.splitext(name)[1]
                    ) or "application/octet-stream"
                    yield {
                        'href': store_url + name,
                        'type': content_type,
                        'name': name,
                        'content_length': stat.st_size,
                        'display_size'  : _format_size(stat.st_size),
                    }
            data = [f for args in os.fwalk(path) for f in file_records(*args)]
            content = { "links": data }    

        self.write_json(content)                  

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

        etag = f"'{mtime}'"
        if self.request.headers.get('If-None-Match') == etag:
            self.set_header('Etag', etag)
            self.set_status(304)
            return

        # Set headers
        content_type = mimetypes.types_map.get(os.path.splitext(full_path)[1]) or "application/octet-stream"
        self.set_header("Content-Type", content_type)       
        self.set_header("Etag", etag)

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

    def create_dnl_url(self, job_id: str, resource: Optional[str]=None):
        """ Store the request and create a download url
        """
        token = logstore.set_json({
            'uuid': job_id,
            'name': resource,
        }, self._ttl)

        proxy_url = self.proxy_url()
        now       = datetime.utcnow().timestamp()
        self.write_json({
            'name': resource,
            'href': f"{proxy_url}dnl/{token}",
            'expire_at': datetime.fromtimestamp(now+self._ttl).isoformat()+'Z',
        })


class StoreHandler(BaseHandler, StoreShellMixIn):
    """ Handle store requests
    """
    def initialize(self, workdir, chunk_size=65536, legacy: bool=False, ttl=30):
        super().initialize()
        self._chunk_size = chunk_size
        self._workdir = workdir
        self._legacy = legacy
        self._ttl = ttl

    async def get(self, uuid: str, resource: Optional[str]=None) -> Awaitable[None]:
        """ Handle GET request
        """
        if resource:
            await self.dnl(uuid, resource)
        else:
            await self.ls(uuid)

    async def put(self, uuid: str, resource: Optional[str]) -> Awaitable[None]:
        """ Handle put actions
        """
        if not uuid:
            raise HTTPError(403, reason="Missing job ID")

        # Get the status for uuid
        job_status = self.application.wpsservice.get_status(uuid)
        if job_status is None:
            raise HTTPError(404, reason="The resource does not exists") 

        command = self.get_argument('COMMAND', default="").lower()
        if command == 'geturl':
            self.create_dnl_url(uuid, resource)
        else:
            raise HTTPError(400, reason=f"Invalid command parameter {command}")


class DownloadHandler(BaseHandler, StoreShellMixIn):
    """ The safe store handler work in two time

        1. Return a tokenized set of  url with a limited ttl
        2. Handle the url by returning the appropriate ressource
    """
    def initialize(self, workdir, query=False,  chunk_size=65536):
        super().initialize()
        self._chunk_size = chunk_size
        self._workdir = workdir

    async def get(self, token):
        """ Handle GET request
        """
        # Download
        uuid, resource = self.get_dnl_params(token)
        await self.download(uuid, resource)

    def get_dnl_params(self, token):
        """ Retrieve the download parameters
        """
        params = logstore.get_json(token)
        if params is None:
            raise HTTPError(403)
        return params['uuid'], params['resource']


