""" Instanciate a pool executor
"""

from qywps.executors import PoolExecutor
from qywps.logger import setup_log_handler
from time import sleep

setup_log_handler()


executor = PoolExecutor();
executor.initialize(processes=[])

sleep(3)
executor.terminate()
print("Exiting")

