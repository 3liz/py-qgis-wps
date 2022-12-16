#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#

__all__ = ['chdir']

import os

from contextlib import contextmanager


@contextmanager
def chdir(directory):
    """ Change directory and restore initial dir
    """
    pwd = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(pwd)
