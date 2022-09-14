#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import logging

from .basehandler import BaseHandler

from typing import Optional

LOGGER = logging.getLogger('SRVLOG')


class StatusHandler(BaseHandler):

    def get_wps_status( self, uuid: Optional[str]=None):
        """ Return the status of the processes
        """ 
        wps_status = self.application.wpsservice.get_status(uuid)
        if uuid is not None and wps_status is None:
            self.set_status(404)
            self.write_json({ 'error': 'process %s not found' % uuid })
            return

        # Replace the status url with the proxy_url if any
        proxy_url = self.proxy_url().rstrip('/')

        # Add additional informations
        def repl( s ):
            s['status_url'] = f"{proxy_url}{s['status_link']}"
            s['store_url']  = f"{proxy_url}/store/{s['uuid']}/"
            s['request']    = f"{proxy_url}/status/{s['uuid']}?key=request"
            del s['status_link']
            return s

        if uuid is not None:
            wps_status = repl(wps_status)
        else:
            wps_status = list(map(repl, wps_status))
        
        self.write_json({ 'status': wps_status })

    def get_wps_request( self, uuid: str ):
        """ Return request infos
        """
        if uuid is None:
            self.set_status(400)
            self.write_json({ 'error': 'Missing uuid' })
            return

        wps_request = self.application.wpsservice.get_status(uuid, key='request')
        if uuid is not None and wps_request is None:
            self.set_status(404)
            self.write_json({ 'error': 'request %s not found' % uuid })
            return

        self.write_json({'request': wps_request})        

    def get( self, uuid: Optional[str]=None):
        """ Return status infos
        """
        key = self.get_argument('KEY', default=None)
        if key == 'request':
            self.get_wps_request(uuid)
        else:
            self.get_wps_status(uuid)

    def delete( self, uuid: Optional[str]=None ):
        """ Delete results
        """
        if uuid is None:
            self.set_status(400)
            self.write_json({ 'error': 'Missing uuid' })
            return
        try:
            success = self.application.wpsservice.delete_results(uuid)
            if not success:
                self.set_status(409) # 409 == Conflict
        except FileNotFoundError:
            self.set_status(404)

    def options(self, endpoint: Optional[str]=None) -> None:
        """ Implement OPTION for validating CORS
        """
        self.set_option_headers('GET, DELETE, OPTIONS')


