##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################


import logging
import os
from abc import ABCMeta, abstractmethod
from urllib.parse import urljoin
from qywps import configuration

LOGGER = logging.getLogger('QYWPS')


class STORE_TYPE:
    PATH = 0
# TODO: cover with tests


class StorageAbstract(object):
    """Data storage abstract class
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def store(self, output):
        """
        :param output: of type IOHandler
        :returns: (type, store, url) where
            type - is type of STORE_TYPE - number
            store - string describing storage - file name, database connection
            url - url, where the data can be downloaded
        """
        pass


class DummyStorage(StorageAbstract):
    """Dummy empty storage implementation, does nothing

    Default instance, for non-reference output request

    >>> store = DummyStorage()
    >>> assert store.store
    """

    def __init__(self):
        """
        """

    def store(self, ouput):
        pass


class FileStorage(StorageAbstract):
    """File storage implementation, stores data to file system

    >>> import ConfigParser
    >>> config = ConfigParser.RawConfigParser()
    >>> config.add_section('FileStorage')
    >>> config.set('FileStorage', 'target', './')
    >>> config.add_section('server')
    >>> config.set('server', 'outputurl', 'http://foo/bar/filestorage')
    >>>
    >>> store = FileStorage()
    >>>
    >>> class FakeOutput(object):
    ...     def __init__(self):
    ...         self.file = self._get_file()
    ...     def _get_file(self):
    ...         tiff_file = open('file.tiff', 'w')
    ...         tiff_file.close()
    ...         return 'file.tiff'
    >>> fake_out = FakeOutput()
    >>> (type, path, url) = store.store(fake_out)
    >>> type == STORE_TYPE.PATH
    True
    """

    def __init__(self):
        """
        """
        config = configuration.get_config('server')
        self.output_url = config.get('outputurl')

    def store(self, output):
        file_name = output.file
        url = self.output_url %  output_file
        LOGGER.debug('File output URI: %s', url)

        return (STORE_TYPE.PATH, output_file, url)


