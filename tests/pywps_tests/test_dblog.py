##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

"""Unit tests for dblog
"""

import unittest

from qywps import configuration
from qywps.executors.logstorage.dblog import get_session
from qywps.executors.logstorage.dblog import ProcessInstance


class DBLogTest(unittest.TestCase):
    """DBGLog test cases"""

    def setUp(self):

        self.database = configuration.get_config('logstorage:db').get('database')

    def test_0_dblog(self):
        """Test qywps.formats.Format class
        """
        session = get_session()
        self.assertTrue(session)

    def test_db_content(self):
        session = get_session()
        null_time_end = session.query(ProcessInstance).filter(ProcessInstance.time_end == None)
        self.assertEqual(null_time_end.count(), 0,
                         'There are no unfinished processes loged')

        null_status = session.query(ProcessInstance).filter(ProcessInstance.status == None)
        self.assertEqual(null_status.count(), 0,
                         'There are no processes without status loged')

        null_percent = session.query(ProcessInstance).filter(ProcessInstance.percent_done == None)
        self.assertEqual(null_percent.count(), 0,
                         'There are no processes without percent loged')

def load_tests(loader=None, tests=None, pattern=None):
    """Load local tests
    """
    if not loader:
        loader = unittest.TestLoader()
    suite_list = [
        loader.loadTestsFromTestCase(DBLogTest)
    ]
    return unittest.TestSuite(suite_list)
