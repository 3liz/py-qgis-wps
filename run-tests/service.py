""" WSGI WPS service
"""

from qywps.app import Service
from qywps.executors.processingexecutor import  ProcessingExecutor

application = Service(processes=[], executor=ProcessingExecutor())

