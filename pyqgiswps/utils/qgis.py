#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Start qgis application
"""
import logging
import os
import sys

from typing import Dict, Optional

version_info = (0, 0, 0)


def setup_qgis_paths() -> str:
    """ Init qgis paths
    """
    qgisPrefixPath = os.environ.get('QGIS_PREFIX_PATH', '/usr/')
    sys.path.append(os.path.join(qgisPrefixPath, "share/qgis/python/plugins/"))
    return qgisPrefixPath


# XXX Apparently we need to keep a reference instance of the qgis_application object
# And not make this object garbage collected
qgis_application = None


def start_qgis_application(
    enable_processing: bool = False,
    verbose: bool = False,
    cleanup: bool = True,
    logger: Optional[logging.Logger] = None,
    logprefix: str = 'Qgis:',
    settings: Optional[Dict] = None) -> 'qgis.core.QgsApplication':   # noqa: F821
    """ Start qgis application

        :param boolean enable_processing: Enable processing, default to False
        :param boolean verbose: Output qgis settings, default to False
        :param boolean cleanup: Register atexit hook to close qgisapplication on exit().
            Note that prevents qgis to segfault when exiting. Default to True.
    """

    os.environ['QGIS_NO_OVERRIDE_IMPORT'] = '1'
    os.environ['QGIS_DISABLE_MESSAGE_HOOKS'] = '1'

    logger = logger or logging.getLogger()
    qgisPrefixPath = setup_qgis_paths()

    from qgis.core import Qgis, QgsApplication
    from qgis.PyQt.QtCore import QCoreApplication

    logger.info("Starting QGIS application: %s", Qgis.QGIS_VERSION)

    global version_info
    version_info = tuple(int(n) for n in Qgis.QGIS_VERSION.split('-')[0].split('.'))

    if QgsApplication.QGIS_APPLICATION_NAME != "QGIS3":
        raise RuntimeError("You need QGIS3 (found %s)" % QgsApplication.QGIS_APPLICATION_NAME)

    #  We MUST set the QT_QPA_PLATFORM to prevent
    #  Qt trying to connect to display in containers
    if os.environ.get('DISPLAY') is None:
        logger.info("Setting offscreen mode")
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'

    # From qgis server
    # Will enable us to read qgis setting file
    QCoreApplication.setOrganizationName(QgsApplication.QGIS_ORGANIZATION_NAME)
    QCoreApplication.setOrganizationDomain(QgsApplication.QGIS_ORGANIZATION_DOMAIN)
    QCoreApplication.setApplicationName(QgsApplication.QGIS_APPLICATION_NAME)

    global qgis_application

    qgis_application = QgsApplication([], False)
    qgis_application.setPrefixPath(qgisPrefixPath, True)

    qgis_application.initQgis()

    if cleanup:
        # Closing QgsApplication on exit will
        # prevent our app to segfault on exit()
        import atexit

        logger.info("%s Installing cleanup hook" % logprefix)

        @atexit.register
        def exitQgis():
            global qgis_application
            if qgis_application:
                qgis_application.exitQgis()
                del qgis_application

    optpath = os.getenv('QGIS_OPTIONS_PATH')
    if optpath:
        # Log qgis settings
        load_qgis_settings(optpath, logger, verbose)

    if settings:
        # Initialize settings
        from qgis.core import QgsSettings
        qgsettings = QgsSettings()
        for k, v in settings.items():
            qgsettings.setValue(k, v)

    if verbose:
        print(qgis_application.showSettings())  # noqa: T201

    # Install logger hook
    install_logger_hook(logger, logprefix, verbose=verbose)

    logger.info("%s Qgis application initialized......" % logprefix)

    if enable_processing:
        init_qgis_processing()
        logger.info("%s QGis processing initialized" % logprefix)

    return qgis_application


def init_qgis_processing():
    """ Initialize processing
    """
    from processing.core.Processing import Processing

    from qgis.analysis import QgsNativeAlgorithms
    from qgis.core import QgsApplication

    QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
    Processing.initialize()


def install_logger_hook(logger: logging.Logger, logprefix: str, verbose: bool = False):
    """ Install message log hook
    """
    from qgis.core import Qgis, QgsApplication
    # Add a hook to qgis  message log

    def writelogmessage(message, tag, level):
        arg = f'{logprefix} {tag}: {message}'
        if level == Qgis.Warning:
            logger.warning(arg)
        elif level == Qgis.Critical:
            logger.error(arg)
        elif verbose:
            # Qgis is somehow very noisy
            # log only if verbose is set
            logger.info(arg)

    messageLog = QgsApplication.messageLog()
    messageLog.messageReceived.connect(writelogmessage)


def load_qgis_settings(optpath, logger, verbose=False):
    """ Load qgis settings
    """
    from qgis.core import QgsSettings
    from qgis.PyQt.QtCore import QSettings

    QSettings.setDefaultFormat(QSettings.IniFormat)
    QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, optpath)
    logger.info("Settings loaded from %s", QgsSettings().fileName())
