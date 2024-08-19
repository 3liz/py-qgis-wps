#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

""" Healthcheck command
"""
import argparse
import http.client as http
import ssl
import sys


def main():
    parser = argparse.ArgumentParser(description="py-qgis-wps healthcheck")
    parser.add_argument('--uri', default="localhost:8080", help="Service URL")
    parser.add_argument('--ssl', action="store_true", help="Use ssl")

    args = parser.parse_args()

    if args.ssl:
        ssl_context = ssl.create_default_context()
        h = http.HTTPSConnection(args.uri, context=ssl_context)
    else:
        h = http.HTTPConnection(args.uri)

    try:
        h.request('HEAD', '/')

        rv = h.getresponse()
        print("Response status:", rv.status)  # noqa: T201
        if rv.status == 200:
            sys.exit(0)
    except Exception as e:
        print("Connection error: %s" % e, file=sys.stderr)  # noqa: T201

    sys.exit(1)
