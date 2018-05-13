#
# Copyright 2018 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
""" Import utilities 
"""

__all__ = ['load_source']


from importlib.util import spec_from_file_location, module_from_spec

def load_source(name, path):
    """ Mimic the deprecated  'imp.load_source' function
    """
    spec = spec_from_file_location(name, path)
    mod  = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

