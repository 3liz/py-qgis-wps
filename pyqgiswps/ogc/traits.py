#
# Copyright 2021 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


registry = {}

def register_trait(cls):
    """ Register trait class according
        to class name
    """
    registry.setdefault(cls.__name__,[]).append(cls)
    return cls


def register_trait_for(name):
    """ Register trait class according
        to given name
    """
    def wrapper(cls):
        registry.setdefault(name,[]).append(cls)
        return cls
    return wrapper


class __Exports:
    def __getattr__(self, name):
        # Search mixins for class name
        return  registry[name]

exports = __Exports()
