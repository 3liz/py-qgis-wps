""" Redis storage for WPS 

    See http://redis-py.readthedocs.io/en/latest/
"""

import os
import json
import logging

from datetime import datetime
from lxml import etree
from collections import namedtuple
from qywps.executors import LOGStore
from qywps.app.WPSResponse import STATUS
from qywps import configuration

import redis

LOGGER = logging.getLogger('QYWPS')


class RedisStore(LOGStore):

    def log_request( self, request_uuid, wps_request):
        """ Create request status

            Called once when the request is handled
        """

        uuid_str = str(request_uuid)

        LOGGER.debug("LOGSTORE: logging request %s", uuid_str)
        record = {
          'uuid': uuid_str,
          'version': wps_request.version,
          'identifier': wps_request.identifier,
          'store_execute': wps_request.store_execute,
          'status': STATUS.NO_STATUS.name,
          'percent_done': 0,
          'message': '',
          'expiration': wps_request.expiration,
          'time_start': datetime.now().isoformat(),
          'time_end': None,
          'pinned': False,
          'timeout': wps_request.timeout
        }

        # Record status
        rv = self._db.hset(self._hstatus, uuid_str, json.dumps(record))
        if not rv:
            LOGGER.error("Failed to record request %s", uuid_str) 

        # Trace the request if requested
        if self._trace:
            self._db.setex("{}:request:{}".format(self._prefix, uuid_str),  wps_request.json, 
                           self._tracexp)
        return record

    def update_response( self, request_uuid, wps_response ):
        """ Update the request status
        """
        # Retrieve the record
        uuid_str = str(request_uuid)

        LOGGER.debug("LOGSTORE: Updating response %s", uuid_str)
        data = self._db.hget(self._hstatus, uuid_str)
        if data is None:
            # The request has not been recorded for any reason
            # log error and record it.
            LOGGER.error("No recorded status for request %s", uuid_str)
            record = log_request(wps_response.wps_request)
        else:
            record = json.loads(data.decode('utf-8'))
        record['message']      = wps_response.message
        record['percent_done'] = wps_response.status_percentage
        record['status']       = wps_response.status.name
        record['timestamp']    = datetime.now().timestamp()

        if wps_response.status >= STATUS.DONE_STATUS:
            now   = datetime.now()
            record['time_end']  = now.isoformat()
            record['expire_at'] = datetime.fromtimestamp(now.timestamp()+record['expiration']).isoformat()

        # Note that hset return 0 if the key already exists but change the value anyway
        self._db.hset(self._hstatus, uuid_str, json.dumps(record))

    def pin_response( self, request_uuid, pin=True ):
        """ Pin response so that it never expires

            Note that it is not allowed to pin a unfinished/failed task
        """
        uuid_str = str(request_uuid)
        LOGGER.debug("LOGSTORE: pinning record %s", uuid_str)
        data = self._db.hget(self._hstatus, str(uuid))
        if data is not None:  
            data   = json.loads(data.decode('utf-8'))
            if STATUS[data['status']] != STATUS.DONE_STATUS:
                return False
            if pin:
                data['pinned']    = True
                data['expire_at'] = None
            else:
                data['pinned']    = False
                data['expire_at'] = datetime.fromtimestamp(now.timestamp()+record['expiration']).isoformat()
            # update the record
            self._db.hset(self._hstatus, uuid_str, json.dumps(record))
            return True
        else:
            raise FileNotFoundError("No status for %s" % uuid_str)


    def write_response( self,  request_uuid, doc ):
        """ Write response doc
        """
        uuid_str = str(request_uuid)
        LOGGER.debug("LOGSTORE: writing response doc %s", uuid_str)
        content = etree.tostring(doc, pretty_print=True, encoding='utf-8')
        rv = self._db.set("{}:response:{}".format(self._prefix, uuid_str), content)
        if not rv:
            LOGGER.error("LOGSTORE: Failed to log response %s", uuid_str)

    def delete_response( self, request_uuid ):
        """ Remove record and response
        """
        uuid_str = str(request_uuid)
        LOGGER.debug("LOGSTORE: deleting record %s", uuid_str)
        p = self._db.pipeline()
        p.delete("{}:response:{}".format(self._prefix, uuid_str))
        p.hdel(self._hstatus, uuid_str)
        p.execute()

    def status_url( self, request_uuid, request ):
        """ Return the url to access status
        """
        host = self._proxy_host
        if not host:
            # Need to return the 'real' host
            host = request.host_url if request else '{host_url}'

        return self._urlpath.format(host_url=host,uuid=request_uuid)
    
    def get_results( self, uuid ):
        """ Return results status
        """
        data = self._db.get("{}:response:{}".format(self._prefix, str(uuid)))
        if data is not None:
            return etree.fromstring(data.decode('utf-8'))    

    @property
    def records( self ):
        """ Iterate through records
        """
        return ((k, json.loads(v.decode('utf-8'))) for k,v in self._db.hscan_iter(self._hstatus))

    def get_status( self, uuid=None ):
        """ Return the status for the given processs

            Return None if the status is not found
        """
        if uuid is None:
            data = [v for (_,v) in self.records]
        else:
            data = self._db.hget(self._hstatus, str(uuid))
            if data is not None:
                data = json.loads(data.decode('utf-8'))
 
        return data


    def init_session(self):
        """ Initialize store session

            see https://redis-py.readthedocs.io/en/latest/ for redis options
        """
        LOGGER.debug("LOGSTORE: Initializing REDIS session")
        cfg = configuration.get_config('logstorage:redis')
        self._config  = cfg
        self._prefix  = cfg.get('hashprefix','qywps')
        self._hstatus = "%s:status"  % self._prefix
        self._trace   = cfg.getboolean('trace_request'  , fallback=False)
        self._tracexp = cfg.getint('trace_expiration'   , fallback=86400)

        srvcfg =  configuration.get_config('server')
        self._urlpath    = srvcfg['status_url']
        self._proxy_host = srvcfg['host_proxy'] 

        self._db  = redis.StrictRedis(
            host = cfg.get('host','localhost'),
            port = cfg.getint('port' , fallback=6379),
            db   = cfg.getint('dbnum', fallback=0))

