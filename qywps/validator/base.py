##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################


from qywps.validator.mode import MODE


def emptyvalidator(data_input, mode):
    """Empty validator will return always false for security reason
    """

    if mode <= MODE.NONE:
        return True
    else:
        return False
