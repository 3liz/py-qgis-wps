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

from .version import __manifest__, __description__
from .runtime import run_server
from .config import (load_configuration,
                     read_config_file,
                     confservice,
                     warn_unsafe_options)
from .logger import setup_log_handler

LOGGER = logging.getLogger('SRVLOG')


def print_version() -> None:

    program = os.path.basename(sys.argv[0])
    print("{program} {version} (build {buildid},commit {commitid})".format(program=program, **__manifest__),
          file=sys.stderr)


def read_configuration(args=None):
    """ Parse command line and read configuration file
    """
    import argparse

    if args is None:
        args = sys.argv

    cli_parser = argparse.ArgumentParser(description=__description__)

    config_file = None

    cli_parser.add_argument('-d', '--debug', action='store_true', default=False, help="Set debug mode")
    cli_parser.add_argument('-c', '--config', metavar='PATH', nargs='?', dest='config',
                            default=config_file, help="Configuration file")
    cli_parser.add_argument('--version', action='store_true',
                            default=False, help="Return version number and exit")
    cli_parser.add_argument('-p', '--port', type=int, help="http port", dest='port',
                            default=argparse.SUPPRESS)
    cli_parser.add_argument('-b', '--bind', metavar='IP', default=argparse.SUPPRESS,
                            help="Interfaces to bind to", dest='interfaces')
    cli_parser.add_argument('-u', '--setuid', default=None, help="uid to switch to", dest='setuid')
    cli_parser.add_argument('-w', '--workers', metavar='NUM', type=int, default=argparse.SUPPRESS,
                            help="number of parallel processes", dest='parallelprocesses')
    cli_parser.add_argument('--dump-config', action='store_true', help="Dump the configuration and exit")

    args = cli_parser.parse_args()

    print_version()
    if args.version:
        sys.exit(1)

    load_configuration()

    if args.config:
        read_config_file(args.config)

    # Override config
    def set_arg(section: str, name: str) -> None:
        if name in args:
            confservice.set(section, name, str(getattr(args, name)))

    set_arg('server', 'port')
    set_arg('server', 'interfaces')
    set_arg('server', 'parallelprocesses')

    if args.debug:
        # Force debug mode
        confservice.set('logging', 'level', 'DEBUG')

    if args.dump_config:
        from .config import write_config
        write_config(sys.stdout)
        sys.exit(0)

    warn_unsafe_options()

    # set log level
    setup_log_handler()
    print(f"Log level set to {logging.getLevelName(LOGGER.level)}\n", file=sys.stderr)

    conf = confservice['server']
    args.port = conf.getint('port')
    args.interfaces = conf['interfaces']
    return args


def main():
    """ Run the server as cli command
    """
    args = read_configuration()
    run_server(port=args.port, address=args.interfaces, user=args.setuid)
