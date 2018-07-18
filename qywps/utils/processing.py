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

from .imp import load_source

def import_providers_modules( providers_path, logger=None ):
    """ Load providers modules
    """
    filepath = os.path.join(providers_path,'__algorithms__.py')
    if not os.path.exists(filepath):
        raise FileNotFoundError(filepath)
    sys.path.append(providers_path)
    if logger:
        logger.info("Loading algorithms providers from %s", filepath)
    return load_source('wps_imported_algorithms',filepath).providers


def register_providers( provider_classes=None, providers_path=None ):
    """ Register providers from provider class list

        IMPORTANT: the processingRegistry does not gain ownership and
        the caller must prevent garbage collection by keeping the ownership of 
        the returned instances
    """
    from qgis.core import QgsApplication
    reg = QgsApplication.processingRegistry()

    # If provider_classes is None, try to load modules
    # from providers_path
    if provider_classes is None:
        if providers_path is None:
            raise TypeError("'providers_path' argument missing")
        provider_classes = import_providers_modules(providers_path)

    for p in provider_classes:
        c = p()
        yield c
        reg.addProvider(c)


def load_styles(styledef_path, logger=None):
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

    if logger:
        logger.info("Found styles file description at %s", filepath)

    from processing.core.Processing import RenderingStyles
    with open(filepath,'r') as fp:
        data = json.load(fp)
        # Replace style name with full path
        for alg in data:
            for key in data[alg]:
                qml = os.path.join(styledef_path,'qml',data[alg][key])
                if not os.path.exists(qml):
                    if logger:
                        logger.warning("Style '%s' not found", qml)
                data[alg][key] = qml
        # update processing rendering styles
        RenderingStyles.styles.update(data)



