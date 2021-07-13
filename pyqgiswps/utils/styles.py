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
import json
import logging

LOGGER = logging.getLogger('SRVLOG')


def load_styles(styledef_path: str) -> None:
    """ Load styles definitions

        The json structure should be the following:

        {
            'algid': {
                'outputname': file.qml
                ...
            }
            ...
        }
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



