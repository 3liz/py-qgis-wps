""" Test parsing processing itputs to WPS inputs
"""
import os

from pathlib import Path
from pyqgiswps.accesspolicy import new_access_policy, DefaultPolicy
from pyqgiswps.filters import blockingfilter
from pyqgiswps.app import Service
from pyqgiswps.tests import HTTPTestCase
from pyqgiswps.executors.processingexecutor import ProcessingExecutor


def test_accesspolicy(rootdir):
    """
    """
    defaultpolicy = DefaultPolicy()
    defaultpolicy.init(Path(rootdir.strpath) / "sample_accesspolicy.yml")

    accesspolicy = new_access_policy()

    assert not defaultpolicy.allow( "not_allowed"  , accesspolicy )

    assert defaultpolicy.allow( "allowed_test1", accesspolicy )
    assert defaultpolicy.allow( "allowed_test2", accesspolicy )

    accesspolicy.add_policy(allow=['new_allowed_process'])
    assert defaultpolicy.allow( "new_allowed_process", accesspolicy )


class TestAccessPolicy(HTTPTestCase):

    def get_filters(self):

        @blockingfilter()
        def access_filter( handler ):
            handler.accesspolicy.add_policy(deny=['pyqgiswps_test:*'],
                                            allow=['pyqgiswps_test:simplebuffer'])

        return [access_filter]

    def test_access_filter(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&request=GetCapabilities')
        client = self.client_for(Service(executor=ProcessingExecutor()))
        rv = client.get(uri, path='')
        assert rv.status_code == 200

        exposed = rv.xpath_text('/wps:Capabilities'
                                  '/wps:ProcessOfferings'
                                  '/wps:Process'
                                  '/ows:Identifier')
        # Check that there is only one exposed pyqgiswps_test
        idents = [x for x in exposed.split() if x.startswith('pyqgiswps_test:')]
        assert idents == ['pyqgiswps_test:simplebuffer']
        




