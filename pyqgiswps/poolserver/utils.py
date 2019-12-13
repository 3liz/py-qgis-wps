#
# Copyright 2020 3liz
# Author David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

""" Pool server utilities
"""

import os

def _get_ipc( name ) -> str:
    ipc_path = '/tmp/qgswps/%s_%s' % (name, os.getpid())
    os.makedirs(os.path.dirname(ipc_path), exist_ok=True)
    return 'ipc://'+ipc_path


WORKER_READY=b"ready"

