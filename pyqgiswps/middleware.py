#
# Copyright 2018 3liz
# Author David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import traceback

import tornado.web

from tornado.web import HTTPError
from tornado.routing import Router

from typing import TypeVar, List, NamedTuple

from .handlers import ErrorHandler
from .accesspolicy import new_access_policy

from pyqgisservercontrib.core.filters import _FilterBase


HandlerDelegate = TypeVar('HandlerDelegate')

LOGGER = logging.getLogger('SRVLOG')


class _Policy(NamedTuple):
    pri: int
    filters: List[_FilterBase]


def load_policies() -> List[_FilterBase]:
    """ Create filter list
    """
    collection = []

    class policy_service:
        @staticmethod
        def add_filters(filters, pri=0):
            if LOGGER.isEnabledFor(logging.DEBUG):
                LOGGER.debug("Adding policy filter(s):\n%s", '\n'.join(str(f) for f in filters))
            collection.append(_Policy(pri, [p for p in filters if isinstance(p, _FilterBase)]))

    import pyqgisservercontrib.core.componentmanager as cm
    cm.register_entrypoints('py_qgis_wps.access_policy', policy_service)

    return collection


class MiddleWareRouter(Router):

    def __init__(self, app: tornado.web.Application, filters: List[_FilterBase] = None) -> None:
        """ Initialize middleware filters
        """
        LOGGER.info("Initializing middleware filters")
        self.app = app
        self.policies = load_policies()

        if filters:
            self.policies.append(_Policy(0, [p for p in filters if isinstance(p, _FilterBase)]))

        # Sort filters
        self.policies.sort(key=lambda p: p.pri, reverse=True)

    def find_handler(self, request, **kwargs) -> HandlerDelegate:
        """ Define middleware prerocessing
        """
        wps_policy_defs = None
        # Find matching paths
        for policy in self.policies:
            for filt in policy.filters:
                # Find the first filter that match the path
                match, path = filt.match(request.path)
                if match:
                    LOGGER.debug("Found matching filter for %s -> %s: %s", request.path, path, filt)
                    request.path = path
                    try:
                        wps_policy_defs = filt.apply(request)
                        break
                    except HTTPError as err:
                        kwargs = {'status_code': err.status_code, 'reason': err.reason}
                        return self.app.get_handler_delegate(request, ErrorHandler, kwargs)
                    except Exception:
                        LOGGER.critical(traceback.format_exc())
                        return self.app.get_handler_delegate(request, ErrorHandler, {'status_code': 500})

        delegate = self.app.find_handler(request, **kwargs)

        if wps_policy_defs:
            # Substitute the default access_policy with a new one
            # and add policy definitions
            handler_kwargs = delegate.handler_kwargs
            if handler_kwargs.get('access_policy'):
                access_policy = new_access_policy()
                for policy_def in wps_policy_defs:
                    access_policy.add_policy(**policy_def)

                handler_kwargs.update(access_policy=access_policy)

        return delegate
