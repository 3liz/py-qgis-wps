""" Redis log storage for WPS

    See http://redis-py.readthedocs.io/en/latest/
"""
import json
import logging
import os
import uuid

from datetime import datetime
from enum import IntEnum
from typing import Iterator, Optional
from uuid import UUID

import redis

from pyqgiswps.config import confservice

LOGGER = logging.getLogger('SRVLOG')


def utcnow():
    return datetime.utcnow().replace(microsecond=0)


class STATUS(IntEnum):
    NO_STATUS = 0
    ACCEPTED_STATUS = 21
    STARTED_STATUS = 25
    DONE_STATUS = 30
    ERROR_STATUS = 40
    DISMISS_STATUS = 50


class LogStore:

    def log_request(self, request_uuid, wps_request):
        """ Create request status

            Called once when the request is handled
        """
        uuid_str = str(request_uuid)

        LOGGER.debug("LOGSTORE: logging request %s", uuid_str)
        record = {
            'conformance': wps_request.conformance(),
            'uuid': uuid_str,
            'version': wps_request.version,
            'identifier': wps_request.identifier,
            'execute_async': wps_request.execute_async,
            'status': STATUS.NO_STATUS.name,
            'percent_done': -1,
            'message': '',
            'map': wps_request.map_uri,
            'expiration': wps_request.expiration,
            'time_start': utcnow().isoformat() + 'Z',
            'time_end': None,
            'pinned': False,
            'timeout': wps_request.timeout,
            'realm': wps_request.realm,
            'status_link': wps_request.status_link,
        }

        # Record status
        rv = self._db.hset(self._hstatus, uuid_str, json.dumps(record))
        if not rv:
            LOGGER.error("Failed to record request %s", uuid_str)

        # Record the request
        self._db.set(f"{self._prefix}:request:{uuid_str}", wps_request.dumps())

        return record

    def set_json(self, value, expire):
        """ Set a value at key 'name', expire is mandatory
        """
        # Create token
        token = str(uuid.uuid4()).replace('-', '')
        self._db.setex('token:' + token, expire, json.dumps(value))
        return token

    def get_json(self, token):
        """ Return the value at key 'name'
        """
        value = self._db.get('token:' + token)
        if value is not None:
            value = json.loads(value.decode('utf-8'))
        return value

    def update_response(self, request_uuid, wps_response):
        """ Update the request status
        """
        # Retrieve the record
        uuid_str = str(request_uuid)

        data = self._db.hget(self._hstatus, uuid_str)
        if data is None:
            # The request has not been recorded for any reason
            # log error and record it.
            LOGGER.error("No recorded status for request %s", uuid_str)
            record = self.log_request(request_uuid, wps_response.wps_request)
        else:
            record = json.loads(data.decode('utf-8'))

        now = utcnow()

        timestamp = now.timestamp()

        current_status = STATUS[record['status']]

        if current_status < STATUS.STARTED_STATUS and wps_response.status == STATUS.STARTED_STATUS:
            # Task started
            record['job_start'] = now.isoformat() + 'Z'
            # Record the actual pid
            # Updating occurs in the worker process
            # We use it to kill workers in 'BUSY' state
            record['pid'] = os.getpid()

        record['message'] = wps_response.message
        record['percent_done'] = wps_response.status_percentage
        record['status'] = wps_response.status.name
        record['timestamp'] = timestamp

        if wps_response.status >= STATUS.DONE_STATUS:
            record['output_files'] = wps_response.output_files
            record['time_end'] = now.isoformat() + 'Z'
            record['expire_at'] = datetime.fromtimestamp(now.timestamp() + record['expiration']).isoformat() + 'Z'

            # Remove pid
            if 'pid' in record:
                del record['pid']

        # Note that hset return 0 if the key already exists but change the value anyway
        self._db.hset(self._hstatus, uuid_str, json.dumps(record))

    def pin_response(self, request_uuid, pin=True):
        """ Pin response so that it never expires

            Note that it is not allowed to pin a unfinished/failed task
        """
        uuid_str = str(request_uuid)
        LOGGER.debug("LOGSTORE: pinning record %s", uuid_str)
        data = self._db.hget(self._hstatus, str(uuid))
        if data is not None:
            record = json.loads(data.decode('utf-8'))
            if STATUS[record['status']] != STATUS.DONE_STATUS:
                return False
            if pin:
                record['pinned'] = True
                record['expire_at'] = None
            else:
                record['pinned'] = False
                record['expire_at'] = datetime.fromtimestamp(
                    utcnow().timestamp() + record['expiration']).isoformat() + 'Z'
            # update the record
            self._db.hset(self._hstatus, uuid_str, json.dumps(record))
            return True
        else:
            raise FileNotFoundError("No status for %s" % uuid_str)

    def write_response(self, request_uuid: str, content: bytes):
        """ Write response doc
        """
        uuid_str = str(request_uuid)
        rv = self._db.set(f"{self._prefix}:response:{uuid_str}", content)
        if not rv:
            LOGGER.error("LOGSTORE: Failed to log response %s", uuid_str)

    def delete_response(self, request_uuid):
        """ Remove record and response
        """
        uuid_str = str(request_uuid)
        LOGGER.debug("LOGSTORE: deleting record %s", uuid_str)
        p = self._db.pipeline()
        p.delete(f"{self._prefix}:response:{uuid_str}")
        p.delete(f"{self._prefix}:request:{uuid_str}")
        p.hdel(self._hstatus, uuid_str)
        p.execute()

    def get_results(self, uuid: str | UUID) -> Optional[bytes]:
        """ Return results status
        """
        data = self._db.get(f"{self._prefix}:response:{uuid!s}")
        if data is not None:
            return data

    @property
    def records(self) -> Iterator:
        """ Iterate through records
        """
        return ((k, json.loads(v.decode('utf-8'))) for k, v in self._db.hscan_iter(self._hstatus))

    def get_request(self, uuid):
        """ Return results status
        """
        data = self._db.get(f"{self._prefix}:request:{uuid!s}")
        if data is not None:
            return json.loads(data.decode('utf-8'))

    def get_status(self, uuid=None, key=None):
        """ Return the status for the given processs

            Return None if the status is not found
        """
        if key == 'request':
            return self.get_request(uuid)

        if uuid is None:
            data = [v for (_, v) in self.records]
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
        cfg = confservice['logstorage:redis']
        self._config = cfg
        self._prefix = cfg.get('prefix', fallback='pyggiswps')
        self._hstatus = "%s:status" % self._prefix

        self._db = redis.StrictRedis(
            host=cfg.get('host', fallback='localhost'),
            port=cfg.getint('port', fallback=6379),
            db=cfg.getint('dbnum', fallback=0))


#
# The one and only one instance of logstore
#

logstore = LogStore()
