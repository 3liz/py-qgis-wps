#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

from .basehandler import ( # noqa F401
    NotFoundHandler,
    ErrorHandler,
)
from .roothandler import ( # noqa F401
    ServerInfosHandler,
    LandingPageHandler,
)
from .owshandler import OWSHandler    # noqa F401
from .processeshandler import ( # noqa F401
    ProcessHandler,
    JobHandler,
    ExecuteHandler,
    ResultHandler,
    ConformanceHandler,
)
from .statushandler import StatusHandler # noqa F401
from .storehandler import ( # noqa F401
    StoreHandler, 
    DownloadHandler,
    LogsHandler,
)
from .oapihandler import OpenApiHandler # noqa F401
