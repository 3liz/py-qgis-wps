#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import sys


def read_manifest():
    from pkg_resources import resource_stream

    # Read build manifest
    manifest = {'commitid': 'n/a', 'buildid': 'n/a', 'version': 'n/a'}
    try:
        manifest.update(line.decode().strip().split('=')[:2] for line in resource_stream('pyqgiswps',
                                                                                         'build.manifest').readlines())
    except Exception as e:
        print(f"Failed to read manifest !: {e}", file=sys.stderr)  # noqa: T201

    return manifest


__manifest__ = read_manifest()

__version__ = __manifest__['version']
__description__ = "QGIS/Processing WPS server"
