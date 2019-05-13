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


LOGGER = logging.getLogger("QYWPS")

from typing import Generator, Iterable, List, Dict, Any

_ProviderItem = namedtuple('_ProviderItem', ('provider','exposed'))

SCRIPTS_PROVIDER_ID='script'

def _register_script_provider(reg, providers):
    """ Register scripts provider for exposition
    """
    p = reg.providerById(SCRIPTS_PROVIDER_ID)
    if p is None:
        LOGGER.error("Cannot find %s provider", SCRIPTS_PROVIDER_ID)
        return

    providers.append(_ProviderItem(p,True))
    

class WPSServerInterfaceImpl:

    def __init__(self, path, with_scripts: bool=True) -> None:

        self._path = path
        self._plugins = {}
        self._providers    = None
        self._with_scripts = with_scripts

    def initialize(self) -> None:
        """  Collect wps plugins
        """
        self._plugins = { p:None for p in find_plugins(self._path) }
        load_styles(self._path)

        if not self._plugins:
            LOGGER.warning("No WPS plugin found in %s", self._path)

    @property
    def plugins(self) -> Dict[str,Any]:
        return self._plugins

    def register_providers(self) -> List[_ProviderItem]:
        """ Register providers
        """
        if self._providers:
            raise RuntimeException("Providers already registered")

        from qgis.core import QgsApplication
        reg = QgsApplication.processingRegistry()

        providers = []
        self._providers = providers
        
        if self._with_scripts:
            _register_script_provider(reg,providers)

        class _WPSServerInterface:
            def registerProvider( self, provider: 'QgsAlgorithmProvider', expose: bool = True ) -> None:
                reg.addProvider(provider)
                # IMPORTANT: the processingRegistry does not gain ownership and
                # the caller must prevent garbage collection by keeping the ownership of 
                # the returned instances
                providers.append(_ProviderItem(provider,expose))

        wpsIface = _WPSServerInterface()

        sys.path.append(self._path)

        for plugin in self._plugins:
            try:
                __import__(plugin)
                package = sys.modules[plugin] 

                # Initialize the plugin
                LOGGER.info("Loaded plugin %s",plugin)
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

    for plugin in glob.glob(path + "/*"):
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


def load_styles(styledef_path):
    """ Load styles definitions

        The json structure should be the following:

        {
            'algid': {
                'outputname': file.qml
                ...
            }
            ...
        {
    """
    filepath = os.path.join(styledef_path,'styles.json')
    if not os.path.exists(filepath):
        return

    LOGGER.info("Found styles file description at %s", filepath)

    from processing.core.Processing import RenderingStyles
    with open(filepath,'r') as fp:
        data = json.load(fp)
        # Replace style name with full path
        for alg in data:
            for key in data[alg]:
                qml = os.path.join(styledef_path,'qml',data[alg][key])
                if not os.path.exists(qml):
                    LOGGER.warning("Style '%s' not found", qml)
                data[alg][key] = qml
        # update processing rendering styles
        RenderingStyles.styles.update(data)



