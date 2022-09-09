#
# Copyright 2022 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import logging
import traceback
import uuid

from .basehandler import HTTPError, BaseHandler

from tornado.escape import json_decode
from pyqgiswps.exceptions import (NoApplicableCode, 
                                  UnknownProcessError)

from pyqgiswps.ogc.api.request import OgcApiRequest

from typing import Optional, TypeVar, NamedTuple

AccessPolicy = TypeVar('AccessPolicy')

LOGGER = logging.getLogger('SRVLOG')


class ApiHandler(BaseHandler):
    """ Handle WPS 3 (OGC API) requests

        See https://ogcapi.ogc.org/processes/overview.html
        See https://github.com/opengeospatial/ogcapi-processes
    """
    def create_request(self):
        wpsrequest = OgcApiRequest()
        wpsrequest.map_uri  = self.get_argument('MAP', default=None)
        wpsrequest.host_url = self.proxy_url()
        return wpsrequest

    def initialize(self, access_policy: AccessPolicy):
        super().initialize()
   
        self.accesspolicy = access_policy

    def format_exception(self, exc: NoApplicableCode) -> None:
        """ Override
            Format exception  based based on RFC 7807
        """
        body = {
            'type': 'ogc-api:exception-report',
            'title': exc.name,
            'status': exc.code,
        }
        if exc.description:
            body.update(detail=exc.description)
        if exc.locator:
            body.update(instance=exc.locator)
        
        self.write_json(body)


class ProcessHandler(ApiHandler):
    """ Handle /process
    """

    def get(self, process_id: Optional[str]=None):
        """ Get Process description
        """
        service = self.application.wpsservice
        wpsrequest = self.create_request()
        if process_id:
            if not self.accesspolicy.allow(process_id):
                raise HTTPError(403, reason="Unauthorized operation")
            try:
                response = wpsrequest.get_process_description(process_id, service)
            except UnknownProcessError:
                raise HTTPError(404, reason=f"Uknown process id: {process_id}") from None
        else:
            response = wpsrequest.get_process_list(service, self.accesspolicy) 
 
        self.write_json(response)

    def options(self, endpoint: Optional[str]=None) -> None:
        """ Implement OPTION for validating CORS
        """
        self.set_option_headers('GET, OPTIONS')


class ExecutePrefs(NamedTuple):
    execute_async: bool = False
    timeout: int = None
    expire: int = None

    def _preference_applied(self, request) -> str:
        """ Return the list of applied prefs
        """
        execute_async = self.execute_async
        timeout = self.timeout
        expire = self.expire

        applied = []
        if execute_async:
            applied.append('respond-async')
        # Timeout was s
        if timeout != request.timeout:
            timeout = None
        if timeout is not None:
            applied.append('wait')
        if expire != request.expiration:
            expire = None
        if expire is not None:
            applied.append('x-expire')
 
        return ','.join(applied)


class ExecuteHandler(ApiHandler):
    """ Handle /process/{process_id}/execution
    """

    def get_execute_prefs(self):
        """ Get execution preferences from 'Prefer' header

            See https://webconcepts.info/concepts/http-preference/
            See https://docs.ogc.org/is/18-062r2/18-062r2.html#toc32
        """
        kwargs = {}
        prefer = self.request.headers.get('Prefer')
        if prefer is not None:
            for pref in (p.strip().lower() for p in prefer.split(',')):
                if pref == 'respond-async': 
                    kwargs['execute_async'] = True
                elif pref.startswith('wait='):
                    try:
                        kwargs['timeout'] = int(pref.split('=')[1])
                    except TypeError:
                        pass
                elif pref.startswith('x-expire='):
                    try:
                        kwargs['expire'] = int(pref.split('=')[1])
                    except TypeError:
                        pass
 
        return ExecutePrefs(**kwargs)

    async def post(self, process_id):
        """ Execute process asynchronously
        """
        service = self.application.wpsservice
        wpsrequest = self.create_request()
        if not self.accesspolicy.allow(process_id):
            raise HTTPError(403, reason="Unauthorized operation")

        try:
            # Parse json body
            doc = json_decode(self.request.body)
        except Exception:
            LOGGER.error(traceback.format_exc())
            raise HTTPError(400, reason="Invalid json body") from None

        # Get preferences
        prefs = self.get_execute_prefs()

        try:
            job_id = uuid.uuid1()
            content = await wpsrequest.execute(
                process_id, job_id, doc, service,
                execute_async=prefs.execute_async,
                timeout=prefs.timeout,
                expire=prefs.expire,
            )
        except UnknownProcessError:
            raise HTTPError(404, reason=f"Uknown process id: {process_id}") from None

        # Set the job id as X header
        self.set_header("X-Job-Id", str(job_id))

        # Asyncchronous response must return the status
        if prefs.execute_async:
            # Retrieve the status
            content = wpsrequest.get_ogcapi_job_status(str(job_id), service)
            if content is None:
                # Something really wrong happened !!!
                LOGGER.critical("Missing job status for job '%s' (process: %s) !", 
                                job_id, process_id)
                raise HTTPError(500)
 
            # See https://docs.ogc.org/is/18-062r2/18-062r2.html#toc26
            # See https://developer.mozilla.org/fr/docs/Web/HTTP/Status/201
            self.set_header("Location", f"{wpsrequest.host_url}jobs/{job_id}")
            self.set_status(201)
          
        # Set Preference-Applied according to actual parameters
        # used
        preference_applied = prefs._preference_applied(wpsrequest)
        if preference_applied:
            self.set_header('Preference-Applied', preference_applied)

        self.write_json(content)

    def options(self, endpoint: Optional[str]=None) -> None:
        """ Implement OPTION for validating CORS
        """
        self.set_option_headers('POST, OPTIONS')


class JobHandler(ApiHandler): 
    """ Handle /jobs
    """
    def get(self, job_id: Optional[str]=None):
        """ Job status
        """
        wpsrequest = self.create_request()
        if job_id is None:
            content = wpsrequest.get_ogcapi_job_list(self.application.wpsservice)
        else:
            content = wpsrequest.get_ogcapi_job_status(job_id, self.application.wpsservice)
            if content is None: 
                raise HTTPError(404, reason="Job not found")        

        self.write_json(content)

    def delete(self, job_id: str):
        """ Delete results
        """
        wpsrequest = self.create_request()
        content =  wpsrequest.get_ogcapi_job_dismiss(job_id, self.application.wpsservice)
        if content is None: 
            raise HTTPError(404, reason="Job not found")        

        self.write_json(content)

    def options(self, endpoint: Optional[str]=None) -> None:
        """ Implement OPTION for validating CORS
        """
        self.set_option_headers('GET, DELETE, OPTIONS')


class ResultHandler(ApiHandler): 
    """ Handle /jobs/{job_id}/results
    """

    def get(self, job_id: str):
        content = self.application.wpsservice.get_results(job_id)
        self.set_header("X-Job-Id", job_id)
        self.write_json(content)

    def options(self, endpoint: Optional[str]=None) -> None:
        """ Implement OPTION for validating CORS
        """
        self.set_option_headers('GET, OPTIONS')


