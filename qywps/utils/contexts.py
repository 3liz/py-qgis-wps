"""
"""

__all__ = ['chdir']

import os

from contextlib import contextmanager

@contextmanager
def chdir( directory ):
    """ Change directory and restore initial dir
    """
    pwd = os.getcwd()
    os.chdir(directory)
    try:
        yield
    finally:
        os.chdir(pwd)

