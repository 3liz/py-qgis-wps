#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Processing utilities
"""

import os
import sys
import json
import logging
import glob
import configparser
import traceback

from collections import namedtuple
from .styles import load_styles

LOGGER = logging.getLogger('SRVLOG')

from typing import Generator, Iterable, List, Dict, Any

_ProviderItem = namedtuple('_ProviderItem', ('provider','exposed'))

def _register_provider(reg: 'QgsProcessingRegistry', provider_id: str, providers: List[_ProviderItem] ) -> None:
    """ Register scripts provider for exposition
    """
    p = reg.providerById(provider_id)
    if p is None:
        LOGGER.error("Processing provider '%s' not found", provider_id)
        return

    LOGGER.debug("= Registering provider '%s'", provider_id)
    providers.append(_ProviderItem(p,True))


class WPSServerInterfaceImpl:

    def __init__(self, with_providers: List[str]) -> None:
        self._plugins = {}
        self._paths = []
        self._providers      = None
        self._with_providers = with_providers

    def initialize(self, path: str) -> None:
        """  Collect wps plugins
        """
        plugins = { p:None for p in find_plugins(path) }
        if not plugins:
            LOGGER.warning("No WPS plugin found in %s", path)
        else:
            self._paths.append(path)

        self._plugins.update(plugins)
        load_styles(path)

    @property
    def plugins(self) -> Dict[str,Any]:
        return self._plugins

    def register_providers(self) -> None:
        """ Register providers
        """
        if self._providers:
            raise RuntimeError("Providers already registered")

        from qgis.core import QgsApplication
        reg = QgsApplication.processingRegistry()

        providers = []
        self._providers = providers
   
        # Register internal/default qgis providers
        for provider_id in self._with_providers:
            _register_provider(reg, provider_id, providers)

        class _WPSServerInterface:
            def registerProvider( self, provider: 'QgsAlgorithmProvider', expose: bool = True ) -> None:
                reg.addProvider(provider)
                # IMPORTANT: the processingRegistry does not gain ownership and
                # the caller must prevent garbage collection by keeping the ownership of 
                # the returned instances
                providers.append(_ProviderItem(provider,expose))

        wpsIface = _WPSServerInterface()

        sys.path.extend(self._paths)

        for plugin in self._plugins:
            try:
                __import__(plugin)
                package = sys.modules[plugin] 

                # Initialize the plugin
                LOGGER.info("Loaded plugin '%s'",plugin)
                self._plugins[plugin] = package.WPSClassFactory(wpsIface)
            except:
                LOGGER.error("Failed to initialize plugin: %s", plugin)
                traceback.print_exc()

    @property
    def providers(self, exposed: bool=True) -> Iterable['QgsAlgorithmProvider']:
        """ Return loaded  providers

            If exposed is True then return only exposed providers 
        """
        if exposed:
            return (p.provider for p in self._providers if p.exposed)
        else:
            return (p.provider for p in self._providers)


def checkQgisVersion(minver: str, maxver: str) -> bool:
    from qgis.core import Qgis

    def to_int(ver):
        major, *ver = ver.split('.')
        major = int(major)
        minor = int(ver[0]) if len(ver) > 0 else 0
        rev   = int(ver[1]) if len(ver) > 1 else 0
        if minor >= 99:
            minor = rev = 0
            major += 1
        if rev > 99:
            rev = 99
        return int("{:d}{:02d}{:02d}".format(major,minor,rev))

    version = to_int(Qgis.QGIS_VERSION.split('-')[0])
    minver  = to_int(minver) if minver else version
    maxver  = to_int(maxver) if maxver else version

    return minver <= version <= maxver

    
def find_plugins(path: str) -> Generator[str,None,None]:
    """ return list of plugins in given path
    """
    from qgis.core import Qgis

    LOGGER.debug("Looking for plugins in %s", path)

    for plugin in glob.glob(os.path.join(path,"*")):
        if not os.path.isdir(plugin):
            continue
        if not os.path.exists(os.path.join(plugin, '__init__.py')):
            continue

        metadatafile = os.path.join(plugin, 'metadata.txt')
        if not os.path.exists(metadatafile):
            continue

        cp = configparser.ConfigParser()

        try:
            with open(metadatafile, mode='rt') as f:
                cp.read_file(f)

            if not cp['general'].getboolean('wps'):
                LOGGER.warning("%s is not a wps plugin", plugin)
                continue

            minver = cp['general'].get('qgisMinimumVersion')
            maxver = cp['general'].get('qgisMaximumVersion')

        except Exception as exc:
            LOGGER.error("Error reading plugin metadata '%s': %s",metadatafile,exc)
            continue

        if not checkQgisVersion(minver,maxver):
            LOGGER.warning("Unsupported version for %s. Discarding", plugin)
            continue

        yield os.path.basename(plugin)


