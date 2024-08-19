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

import configparser
import logging
import sys
import traceback

from collections import namedtuple
from pathlib import Path
from typing import Any, Dict, Generator, Iterable, List

from .styles import load_styles

LOGGER = logging.getLogger('SRVLOG')

_ProviderItem = namedtuple('_ProviderItem', ('provider', 'exposed'))


def _register_provider(reg: 'QgsProcessingRegistry', provider_id: str,  # noqa: F821
                       providers: List[_ProviderItem]):
    """ Register scripts provider for exposition
    """
    p = reg.providerById(provider_id)
    if p is None:
        LOGGER.error("Processing provider '%s' not found", provider_id)
        return

    LOGGER.debug("= Registering provider '%s'", provider_id)
    providers.append(_ProviderItem(p, True))


class WPSServerInterfaceImpl:

    def __init__(self, with_providers: List[str]):
        self._plugins = {}
        self._paths = []
        self._providers = None
        self._with_providers = with_providers

    def initialize(self, path: str):
        """  Collect wps plugins
        """
        path = Path(path)
        plugins = {p: None for p in find_plugins(path)}
        if not plugins:
            LOGGER.warning("No WPS plugin found in %s", path)
        else:
            self._paths.append(str(path))

        self._plugins.update(plugins)
        load_styles(path)

    @property
    def plugins(self) -> Dict[str, Any]:
        return self._plugins

    def register_providers(self):
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
            def registerProvider(self, provider: 'QgsAlgorithmProvider', expose: bool = True):   # noqa: F821
                reg.addProvider(provider)
                # IMPORTANT: the processingRegistry does not gain ownership and
                # the caller must prevent garbage collection by keeping the ownership of
                # the returned instances
                providers.append(_ProviderItem(provider, expose))

        wpsIface = _WPSServerInterface()

        sys.path.extend(self._paths)

        for plugin in self._plugins:
            try:
                __import__(plugin)
                package = sys.modules[plugin]

                # Initialize the plugin
                LOGGER.info("Loaded plugin '%s'", plugin)
                self._plugins[plugin] = package.WPSClassFactory(wpsIface)

                # Load style from plugin packeges directory
                load_styles(Path(package.__file__).parent)
            except Exception:
                LOGGER.error("Failed to initialize plugin: %s", plugin)
                traceback.print_exc()

    @property
    def providers(self, exposed: bool = True) -> Iterable['QgsAlgorithmProvider']:  # noqa: F821
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
        rev = int(ver[1]) if len(ver) > 1 else 0
        if minor >= 99:
            minor = rev = 0
            major += 1
        if rev > 99:
            rev = 99
        return int(f"{major:d}{minor:02d}{rev:02d}")

    version = to_int(Qgis.QGIS_VERSION.split('-')[0])
    minver = to_int(minver) if minver else version
    maxver = to_int(maxver) if maxver else version

    return minver <= version <= maxver


def find_plugins(path: Path) -> Generator[str, None, None]:
    """ return list of plugins in given path
    """
    LOGGER.debug("Looking for plugins in %s", path)

    for plugin in path.glob("*"):
        if not plugin.is_dir():
            continue
        if not (plugin / '__init__.py').exists():
            continue

        metadatafile = plugin / 'metadata.txt'
        if not metadatafile.exists():
            continue

        cp = configparser.ConfigParser()

        try:
            with metadatafile.open(mode='rt') as f:
                cp.read_file(f)

            if not cp['general'].getboolean('wps'):
                LOGGER.warning("%s is not a wps plugin", plugin)
                continue

            minver = cp['general'].get('qgisMinimumVersion')
            maxver = cp['general'].get('qgisMaximumVersion')

        except Exception as exc:
            LOGGER.error("Error reading plugin metadata '%s': %s", metadatafile, exc)
            continue

        if not checkQgisVersion(minver, maxver):
            LOGGER.warning("Unsupported version for %s. Discarding", plugin)
            continue

        yield plugin.name
