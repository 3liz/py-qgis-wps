#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

import os
import sys
import logging

from .version import __version__, __description__
from .runtime import run_server
from .config import get_config, set_config, load_configuration, read_config_file
from .logger import setup_log_handler

LOGGER=logging.getLogger('SRVLOG')

def print_version(config):
    from .version import __version__
    program = os.path.basename(sys.argv[0])
    print("{name} {version}".format(name=program, version=__version__))


def read_configuration(args=None):
    """ Parse command line and read configuration file
    """
    import argparse

    if args is None:
        args = sys.argv

    cli_parser = argparse.ArgumentParser(description=__description__)

    config_file = None
    config = get_config('server')

    cli_parser.add_argument('-d','--debug', action='store_true', default=False, help="Set debug mode")
    cli_parser.add_argument('-c','--config', metavar='PATH', nargs='?', dest='config',
            default=config_file, help="Configuration file")
    cli_parser.add_argument('--version', action='store_true',
            default=False, help="Return version number and exit")
    cli_parser.add_argument('-p','--port'    , type=int, help="http port", dest='port', default=8080)
    cli_parser.add_argument('-b','--bind'    , metavar='IP',  default='0.0.0.0', help="Interface to bind to", dest='interface')
    cli_parser.add_argument('-u','--setuid'  , default=None, help="uid to switch to", dest='setuid')
    cli_parser.add_argument('-w','--workers' , metavar='NUM', type=int, default=argparse.SUPPRESS, 
            help="number of parallel processes", dest='parallelprocesses')

    args = cli_parser.parse_args()

    if args.version:
        print_version(config)
        sys.exit(1)

    if args.config:
        read_config_file(args.config)

    # Override config
    if 'parallelprocesses' in args:
        set_config('server', 'parallelprocesses', str(args.parallelprocesses))

    if args.debug:
        # Force debug mode
        set_config('logging', 'level', 'DEBUG')

    # set log level
    setup_log_handler()
    print("Log level set to {}\n".format(logging.getLevelName(LOGGER.level)), file=sys.stderr)
    return args



def main():
    """ Run the server as cli command
    """
    args = read_configuration()
    run_server( port=args.port, address=args.interface, user=args.setuid ) 




