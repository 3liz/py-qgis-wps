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

from .basehandler import BaseHandler, DownloadMixIn
from .processeshandler import RealmController

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


class StoreShellMixIn(DownloadMixIn):
    """ Store api implementation
    """

    # XXX DEPRECATED - will be removed at version 1.9
    def legacy_resource_list(self, workdir: Path, uuid: str):
        # Only if admin
        if self.realm_enabled():
            raise HTTPError(401)
        # Legacy json schema
        store_url = f"{self.proxy_url()}store/{uuid}/"
    
        def file_records(rootdir, dirs, files, rootfd):
            root = Path(rootdir)
            for file in files:
                stat  = os.stat(file, dir_fd=rootfd)
                name  = (root / file).relative_to(workdir).as_posix()
                yield {
                    'name': name,
                    'content_length': stat.st_size,
                    'store_url'     : f"{store_url}{name}",
                    'display_size'  : _format_size(stat.st_size),
                }
        data = [f for args in os.fwalk(workdir) for f in file_records(*args)]
        self.write_json({"files":data})       

    async def ls( self, uuid: str):
        """ List all files in workdir
        """
        workdir = Path(self._workdir, uuid)
        if not workdir.is_dir():
            raise HTTPError(404, reason="The resource does not exists")

        if self._legacy:
            # XXX DEPRECATED - will be removed at version 1.9
            self.legacy_resource_list(workdir)
            return

        store_url = f"{self.proxy_url()}jobs/{uuid}/files"

        if self.realm_enabled():

            job_status = self.application.wpsservice.get_status(uuid)
            if job_status is None:
                raise HTTPError(404, reason="The resource does not exists") 

            # Restrict to output files
            def file_records(files):
                for name in files:
                    path = workdir.joinpath(name)
                    if not path.is_file():
                        continue
                    content_type = mimetypes.types_map.get(path.suffix)
                    size = path.stat().st_size
                    yield {
                        'href': f"{store_url}/{name}",
                        'type': content_type or "application/octet-stream",
                        'name': name,
                        'content_length': size,
                        'display_size'  : _format_size(size),
                    }
            data = list(file_records(job_status.get('output_files',[])))
        else:
            def file_records(rootdir, dirs, files, rootfd):
                root = Path(rootdir)
                for file in files:
                    stat = os.stat(file, dir_fd=rootfd)
                    path = root.joinpath(file).relative_to(workdir)
                    content_type = mimetypes.types_map.get(path.suffix)
                    yield {
                        'href': f"{store_url}/{path}",
                        'type': content_type or "application/octet-stream",
                        'name': path.as_posix(),
                        'content_length': stat.st_size,
                        'display_size'  : _format_size(stat.st_size),
                    }
            data = [f for args in os.fwalk(workdir) for f in file_records(*args)]
            
        self.write_json({"links": data})    

    async def dnl( self, uuid, filename, content_type: Optional[str]=None):
        """ Return output file from process working dir
       """
        path = Path(self._workdir, uuid, filename)
        # Set aggresive browser caching since the resource
        # is not going to change
        await self.download(path, content_type, cache_control="max-age=86400")

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


class StoreHandlerBase(BaseHandler, StoreShellMixIn, RealmController):

    def initialize(self, workdir, chunk_size=65536, legacy: bool=False, ttl=30):
        super().initialize()
        self._chunk_size = chunk_size
        self._workdir = workdir
        self._legacy = legacy
        self._ttl = ttl


class StoreHandler(StoreHandlerBase):
    """ Handle store requests
    """
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
            raise HTTPError(400, reason="Missing job ID")

        # Get the status for uuid
        job_status = self.application.wpsservice.get_status(uuid)
        if job_status is None:
            raise HTTPError(404, reason="The resource does not exists") 

        if self.realm_enabled():
            allowed_files = job_status.get('output_files',[])
            if resource not in allowed_files:
                raise HTTPError(401)

        command = self.get_argument('COMMAND', default="").lower()
        if command == 'geturl':
            self.create_dnl_url(uuid, resource)
        else:
            raise HTTPError(400, reason=f"Invalid command parameter {command}")


class DownloadHandler(StoreHandlerBase):
    """ The safe store handler work in two time

        1. Return a tokenized set of  url with a limited ttl
        2. Handle the url by returning the appropriate ressource
    """
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


class LogsHandler(StoreHandlerBase):
    """ Retrun log text content
    """
    async def get(self, job_id) -> Awaitable[None]:
        """ Handle GET request
        """
        # Only admin can see this
        if self.realm_enabled():
            raise HTTPError(403)

        await self.dnl(job_id, "processing.log", 
                       content_type="text/plain; charset=utf-8")



