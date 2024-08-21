#
# Copyright 2020 3liz
# Author David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""" Cache manager for Qgis Projects
"""

import logging
import urllib.parse

from datetime import datetime
from functools import partial
from typing import (
    Callable,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
)
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsMapLayer,
    QgsProject,
    QgsProjectBadLayerHandler,
    QgsProjectStorage,
)
from qgis.server import QgsServerProjectUtils

from pyqgisservercontrib.core import componentmanager

from ..config import confservice
from ..utils.lru import lrucache

# Import default handlers for auto-registration
from .handlers import *  # noqa: F403

LOGGER = logging.getLogger('SRVLOG')


class CacheDetails(NamedTuple):
    project: QgsProject
    timestamp: datetime


class StrictCheckingError(Exception):
    pass


class PathNotAllowedError(Exception):
    pass


CACHE_MANAGER_CONTRACTID = '@3liz.org/cache-manager;1'


def _merge_qs(query1: str, query2: str) -> str:
    """ Merge query1 with query2 but coerce values
        from query1
    """
    params_1 = parse_qs(query1)
    params_2 = parse_qs(query2)
    params_2.update(params_1)
    return '&'.join(f'{k}={v[0]}' for k, v in params_2.items())


class QgisStorageHandler:
    """ Handler for handling Qgis supported storage
        throught the `QgsProjectStorage` api.
    """

    def __init__(self):
        pass

    def get_storage_metadata(self, uri: str) -> QgsProjectStorage.Metadata:
        # Check out for storage
        storage = QgsApplication.projectStorageRegistry().projectStorageFromUri(uri)
        if not storage:
            LOGGER.error("No project storage found for %s", uri)
            raise FileNotFoundError(uri)
        res, metadata = storage.readProjectStorageMetadata(uri)
        if not res:
            LOGGER.error("Failed to read storage metadata for %s", uri)
            raise FileNotFoundError(uri)
        return metadata

    def get_modified_time(self, url: urllib.parse.ParseResult) -> datetime:
        """ Return the modified date time of the project referenced by its url
        """
        metadata = self.get_storage_metadata(urlunparse(url))
        return metadata.lastModified.toPyDateTime()

    def get_project(
        self,
        url: urllib.parse.ParseResult,
        project: Optional[QgsProject] = None,
        timestamp: Optional[datetime] = None,
    ) -> Tuple[QgsProject, datetime]:
        """ Create or return a project
        """
        uri = urlunparse(url)

        metadata = self.get_storage_metadata(uri)
        modified_time = metadata.lastModified.toPyDateTime()

        if timestamp is None or timestamp < modified_time:
            cachmngr = componentmanager.get_service('@3liz.org/cache-manager;1')
            project = cachmngr.read_project(uri)
            timestamp = modified_time

        return project, timestamp


@componentmanager.register_factory(CACHE_MANAGER_CONTRACTID)
class QgsCacheManager:
    """ Handle Qgis project cache
    """

    def __init__(self):
        """ Initialize cache

            :param size: size of the lru cache
        """
        cnf = confservice['projects.cache']

        size = cnf.getint('size')

        self._create_project = QgsProject
        self._cache = lrucache(size)
        self._strict_check = cnf.getboolean('strict_check')
        self._trust_layer_metadata = cnf.getboolean('trust_layer_metadata')
        self._disable_getprint = cnf.getboolean('disable_getprint')
        self._aliases = {}
        self._default_scheme = cnf.get('default_handler', fallback='file')

        allowed_schemes = cnf.get('allow_storage_schemes')
        if allowed_schemes != '*':
            allowed_schemes = [s.strip() for s in allowed_schemes.split(',')]
        self._allowed_schemes = allowed_schemes

        # Set the base url for file protocol
        self._aliases['file'] = 'file:///%s/' % cnf.get('rootdir').strip('/')

        if self._disable_getprint:
            LOGGER.info("** Cache: Getprint disabled")

        if self._trust_layer_metadata:
            LOGGER.info("** Cache: Trust Layer Metadata on")

        # Load protocol handlers
        componentmanager.register_entrypoints('qgssrv_contrib_protocol_handler')

    @property
    def trust_mode_on(self) -> bool:
        return self._trust_layer_metadata

    def clear(self):
        """ Clear the whole cache
        """
        self._cache.clear()

    def remove_entry(self, key: str):
        """ Remove cache entry
        """
        del self._cache[key]

    def resolve_alias(self, key: str) -> urllib.parse.ParseResult:
        """ Resolve scheme from configuration variables
        """
        url = urlparse(key)
        scheme = url.scheme or self._default_scheme
        LOGGER.debug("Resolving '%s' protocol", scheme)
        baseurl = self._aliases.get(scheme)
        if not baseurl:
            try:
                # Check for user-defined scheme
                baseurl = confservice.get('projects.schemes', scheme.replace('-', '_').lower())
            except KeyError:
                pass
            else:
                LOGGER.info("Scheme '%s' aliased to %s", scheme, baseurl)
                self._aliases[scheme] = baseurl
        if baseurl:
            if '{path}' in baseurl:
                url = urlparse(baseurl.format(path=url.path))
            else:
                baseurl = urlparse(baseurl)
                # Build a new query from coercing with base url params
                query = _merge_qs(baseurl.query, url.query)
                # XXX Note that the path of the base url must be terminated by '/'
                # otherwise urljoin() will replace the base name - may be not what we want
                url = urlparse(urljoin(baseurl.geturl(), url.path + '?' + query))

        return url

    def get_project_factory(self, key: str) -> Callable:
        """ Return project store create function for the given key
        """
        url = self.resolve_alias(key)

        scheme = url.scheme or self._default_scheme
        # Check for allowed schemes
        if self._allowed_schemes != '*' and scheme not in self._allowed_schemes:
            LOGGER.error("Scheme %s not allowed", scheme)
            raise PathNotAllowedError(key)

        # Retrieve the protocol-handler
        try:
            store = componentmanager.get_service(f'@3liz.org/cache/protocol-handler;1?scheme={scheme}')
        except componentmanager.FactoryNotFoundError:
            LOGGER.warning("No protocol handler found for %s: using Qgis storage handler", scheme)
            # Fallback to Qgis storage handler
            store = QgisStorageHandler()

        return partial(store.get_project, url)

    def update_entry(self, key: str) -> bool:
        """ Update the cache

            :param key: The key of the entry to update
            :param force: Force updating entry

            :return: true if the entry has been updated
        """
        get_project = self.get_project_factory(key)

        # Get details for the project
        details = self._cache.peek(key)
        if details is not None:
            project, timestamp = get_project(**details._asdict())
            updated = timestamp != details.timestamp
        else:
            project, timestamp = get_project()
            updated = True
        self._cache[key] = CacheDetails(project, timestamp)
        return updated

    def peek(self, key: str) -> CacheDetails:
        """ Return entry if it exists
        """
        return self._cache.peek(key)

    def lookup(self, key: str) -> Tuple[QgsProject, bool]:
        """ Lookup entry from key
        """
        updated = self.update_entry(key)
        return self._cache[key].project, updated

    def read_project(self, path: str) -> QgsProject:
        """ Read project from path

            May be used by protocol-handlers to instanciate project
            from path.
        """
        LOGGER.debug("Reading Qgis project %s", path)

        # see https://github.com/qgis/QGIS/pull/49266
        project = self._create_project(capabilities=Qgis.ProjectCapabilities())
        readflags = Qgis.ProjectReadFlags()
        if self._trust_layer_metadata:
            readflags |= Qgis.ProjectReadFlag.FlagTrustLayerMetadata
        if self._disable_getprint:
            readflags |= Qgis.ProjectReadFlag.FlagDontLoadLayouts

        badlayerh = BadLayerHandler()
        project.setBadLayerHandler(badlayerh)
        project.read(path)
        if self._strict_check and not badlayerh.validateLayers(project):
            raise StrictCheckingError
        return project


class BadLayerHandler(QgsProjectBadLayerHandler):

    def __init__(self):
        super().__init__()
        self.badLayerNames = set()

    def handleBadLayers(self, layers: Sequence[QgsMapLayer]):
        """ See https://qgis.org/pyqgis/3.0/core/Project/QgsProjectBadLayerHandler.html
        """
        super().handleBadLayers(layers)

        nameElements = (lyr.firstChildElement("layername") for lyr in layers if lyr)
        self.badLayerNames = {elem.text() for elem in nameElements if elem}

    def validateLayers(self, project: QgsProject) -> bool:
        """ Check layers

            If layers are excluded do not count them as bad layers
            see https://github.com/qgis/QGIS/pull/33668
        """
        if self.badLayerNames:
            LOGGER.debug("Found bad layers: %s", self.badLayerNames)
            restricteds = set(QgsServerProjectUtils.wmsRestrictedLayers(project))
            return self.badLayerNames.issubset(restricteds)
        return True


cacheservice = componentmanager.get_service(CACHE_MANAGER_CONTRACTID)
