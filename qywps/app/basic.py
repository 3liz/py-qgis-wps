##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
#                                                                #
# Copyright 2018 3liz                                            #
# Author: David Marteau                                          #
#                                                                #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import logging
import lxml
from qywps import __version__, NAMESPACES


def xpath_ns(el, path):
    return el.xpath(path, namespaces=NAMESPACES)


