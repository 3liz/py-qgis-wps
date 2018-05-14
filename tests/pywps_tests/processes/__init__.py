##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################


from qywps import Process
from qywps.inout import LiteralInput

class SimpleProcess(Process):
    identifier = "simpleprocess"

    def __init__(self):
        self.add_input(LiteralInput())
