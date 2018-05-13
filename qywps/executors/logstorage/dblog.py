#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Original parts are Copyright 2016 OSGeo Foundation,            
# represented by PyWPS Project Steering Committee,               
# and released under MIT license.                                
# Please consult PYWPS_LICENCE.txt for details
#

"""
Implementation of logging for QYWPS
"""

import logging
from lxml import etree
from qywps import configuration
from qywps.exceptions import NoApplicableCode
import sqlite3
import datetime
import pickle
import json
import os

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, VARCHAR, Float, DateTime, BLOB
from sqlalchemy.orm import sessionmaker

from  qywps.executors import LOGStore as LOGStoreBase

LOGGER = logging.getLogger('QYWPS')
_SESSION_MAKER = None

config = configuration.get_config('logstorage:db')

_tableprefix = config.get('prefix')
_schema = config.get('schema')

Base = declarative_base()


class ProcessInstance(Base):
    __tablename__ = '{}requests'.format(_tableprefix)

    uuid = Column(VARCHAR(255), primary_key=True, nullable=False)
    pid = Column(Integer, nullable=False)
    operation = Column(VARCHAR(30), nullable=False)
    version = Column(VARCHAR(5), nullable=False)
    time_start = Column(DateTime(), nullable=False)
    time_end = Column(DateTime(), nullable=True)
    identifier = Column(VARCHAR(255), nullable=True)
    message = Column(String, nullable=True)
    percent_done = Column(Float, nullable=True)
    status = Column(Integer, nullable=True)


class RequestInstance(Base):
    __tablename__ = '{}stored_requests'.format(_tableprefix)

    uuid = Column(VARCHAR(255), primary_key=True, nullable=False)
    request = Column(BLOB, nullable=False)


def log_request(uuid, request):
    """Write OGC WPS request (only the necessary parts) to database logging
    system
    """

    pid = os.getpid()
    operation = request.operation
    version = request.version
    time_start = datetime.datetime.now()
    identifier = _get_identifier(request)

    session = get_session()
    request = ProcessInstance(
        uuid=str(uuid), pid=pid, operation=operation, version=version,
        time_start=time_start, identifier=identifier)

    session.add(request)
    session.commit()
    session.close()
    # NoApplicableCode("Could commit to database: {}".format(e.message))


def get_running():
    """Returns running processes ids
    """

    session = get_session()
    running = session.query(ProcessInstance).filter(
        ProcessInstance.percent_done < 100).filter(
            ProcessInstance.percent_done > -1)

    return running


def get_stored():
    """Returns running processes ids
    """

    session = get_session()
    stored = session.query(RequestInstance)

    return stored


def get_first_stored():
    """Returns running processes ids
    """

    session = get_session()
    request = session.query(RequestInstance).first()

    return request


def update_response(uuid, response):
    """Writes response to database
    """

    session = get_session()
    message = None
    status_percentage = None
    status = None

    if hasattr(response, 'message'):
        message = response.message
    if hasattr(response, 'status_percentage'):
        status_percentage = response.status_percentage
    if hasattr(response, 'status'):
        status = response.status

        if status == '200 OK':
            status = 3
        elif status == 400:
            status = 0

    requests = session.query(ProcessInstance).filter_by(uuid=str(uuid))
    if requests.count():
        request = requests.one()
        request.time_end = datetime.datetime.now()
        request.message = message
        request.percent_done = status_percentage
        request.status = status
        session.commit()
        session.close()


def _get_identifier(request):
    """Get operation identifier
    """

    if request.operation == 'execute':
        return request.identifier
    elif request.operation == 'describeprocess':
        if request.identifiers:
            return ','.join(request.identifiers)
        else:
            return None
    else:
        return None


def get_session():
    """Get Connection for database
    """

    LOGGER.debug('Initializing database connection')
    global _SESSION_MAKER

    database = config.get('database')
    echo = config.getboolean('echo', fallback=True)
    try:
        engine = sqlalchemy.create_engine(database, echo=echo)
    except sqlalchemy.exc.SQLAlchemyError as e:
        raise NoApplicableCode("Could not connect to database: {}".format(e.message))

    Session = sessionmaker(bind=engine)
    ProcessInstance.metadata.create_all(engine)
    RequestInstance.metadata.create_all(engine)

    _SESSION_MAKER = Session

    return _SESSION_MAKER()


def store_process(uuid, request):
    """Save given request under given UUID for later usage
    """

    session = get_session()
    request = RequestInstance(uuid=str(uuid), request=request.json)
    session.add(request)
    session.commit()
    session.close()


def remove_stored(uuid):
    """Remove given request from stored requests
    """

    session = get_session()
    request = session.query(RequestInstance).filter_by(name='uuid').first()
    session.delete(request)
    session.commit()
    session.close()


# 
# Implement DBStore base on dblog
#

class DBStore(LOGStoreBase):

    def __init__(self):
        super(DBStore, self).__init__()
        self._file_path  = configuration.get_config('server').get('outputpath')

    def log_request( self, request_uuid, wps_request):
        """
        """
        log_request( request_uuid, wps_request)

    def update_response( self, request_uuid, wps_response ):
        """ Log input request 
        """
        update_response( request_uuid, wps_response )

    def _status_location(self, uuid):
        return os.path.join(self._file_path, str(uuid)) + '.xml'

    def write_response( self,  request_uuid, doc ):
        """ Write response doc
        """
        status_location = self._status_location( request_uuid )
        # TODO: check if file/directory is still present, maybe deleted in mean time
        with open(status_location, 'w') as f:
            f.write(etree.tostring(doc, pretty_print=True, encoding='utf-8').decode('utf-8'))
            f.flush()
            os.fsync(f.fileno())

    def get_results( self, uuid ):
        """ Return results status
        """
        status_location = self._status_location( request_uuid )
        if os.path.exists(status_location):
            return etree.parse(status_location)
    
    def get_status( self, uuid=None, *kwargs):
        """
        """
        raise NotImplementedError

 
