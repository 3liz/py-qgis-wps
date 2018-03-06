""" Wrapper around qgis processing context
"""

import os
import logging

from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

from qgis.core import (QgsProcessingContext,)
from qywps.utils.filecache import FileCache
from qywps.utils.decorators import singleton

from qywps import configuration

from qgis.core import QgsProject

LOGGER = logging.getLogger('QYWPS')

@singleton
class _Cache(FileCache):

    def __init__(self):
        config    = configuration.get_config('cache')
        cachesize = config.getint('size')
        rootdir   = Path(config['rootdir'])

        if not rootdir.exists():
            raise FileNotFoundError(str(rootdir))
        if not rootdir.is_absolute():
            raise ValueError("cache rootdir must be an absolute path: found %s" % rootdir)

        class _Store:
            def getpath(self, key, exists=False):
                # XXX Security: strip leading/trailing slash
                key = key.strip('/')
                path = rootdir / key
                path = path.with_suffix('.qgs')
                if not path.exists():
                    raise FileNotFoundError(str(path))

                # Get modification time for the file
                timestamp = datetime.fromtimestamp(path.stat().st_mtime)
                return str(path), timestamp

        # Init FileCache
        super().__init__(size=cachesize, store=_Store())  


def cache_lookup( uri ):
    c = _Cache()
    return c.lookup(uri.path)


class Context(QgsProcessingContext):

    def __init__(self, workdir, map_uri=None):
        super().__init__()
        self.workdir = workdir

        if map_uri is not None:
            self.map_uri = urlparse(map_uri)
            self.setProject(cache_lookup(self.map_uri))
        else:
            LOGGER.warning("No map url defined, inputs may be incorrect !")    
            self.uri = None

        # Create the destination project
        self.destination_project = QgsProject()

    def write_result(self, workdir, name):
        """ Save results to disk
        """
        LOGGER.debug("Writing Results to %s", workdir)
        return self.destination_project.write(os.path.join(workdir,name+'.qgs'))

