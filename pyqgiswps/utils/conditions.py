#
# Define pre/post condition assertion
#
from typing import Optional


class PreconditionError(Exception):
    pass


class PostconditionError(Exception):
    pass


def assert_precondition(condition: bool, message: Optional[str] = None):
    if not condition:
        raise PreconditionError(message or "Pre condition failed")


def assert_postcondition(condition: bool, message: Optional[str] = None):
    if not condition:
        raise PostconditionError(message or "Post condition failed")
