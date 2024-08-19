""" Test parsing processing itputs to WPS inputs
"""

from pathlib import Path

from pyqgisservercontrib.core.filters import policy_filter
from pyqgiswps.accesspolicy import DefaultPolicy, new_access_policy
from pyqgiswps.executors.processfactory import get_process_factory
from pyqgiswps.tests import HTTPTestCase


def test_accesspolicy(rootdir):
    """
    """
    defaultpolicy = DefaultPolicy()
    defaultpolicy.init(rootdir / "sample_accesspolicy.yml")

    accesspolicy = new_access_policy()

    assert not defaultpolicy.allow("not_allowed", accesspolicy)

    assert defaultpolicy.allow("allowed_test1", accesspolicy)
    assert defaultpolicy.allow("allowed_test2", accesspolicy)

    accesspolicy.add_policy(allow=['new_allowed_process'])
    assert defaultpolicy.allow("new_allowed_process", accesspolicy)


class TestAccessPolicy(HTTPTestCase):

    def get_processes(self):
        return get_process_factory()._create_qgis_processes()

    def get_filters(self):

        @policy_filter()
        def access_filter(_):
            return [dict(deny=['pyqgiswps_test:*'], allow=['pyqgiswps_test:simplebuffer'])]

        return [access_filter]

    def test_access_filter(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&request=GetCapabilities')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 200

        exposed = rv.xpath_text('/wps:Capabilities'
                                  '/wps:ProcessOfferings'
                                  '/wps:Process'
                                  '/ows:Identifier')
        # Check that there is only one exposed pyqgiswps_test
        idents = [x for x in exposed.split() if x.startswith('pyqgiswps_test:')]
        assert idents == ['pyqgiswps_test:simplebuffer']

    def test_execute_forbidden_process(self):
        """ Test processing executor 'Execute' request
        """
        uri = ('/ows/?service=WPS&request=Execute&Identifier=pyqgiswps_test:testcopylayer&Version=1.0.0'
                               '&MAP=france_parts&DATAINPUTS=INPUT=france_parts%3BOUTPUT=france_parts_2')
        rv = self.client.get(uri, path='')
        assert rv.status_code == 403


class TestLizmapAccessPolicy(HTTPTestCase):

    def get_processes(self):
        return get_process_factory()._create_qgis_processes()

    def get_filters(self):

        from pyqgisservercontrib.lizmapacl import filters

        policyfile = Path(__file__).parent.parent.joinpath('lizmap_accesspolicy.yml')
        return filters.get_policies(policyfile)

    def test_execute_return_403(self):
        """ Test map profile
        """
        uri = (
            '?service=WPS'
            '&request=Execute'
            '&Identifier=pyqgiswps_test:testcopylayer'
            '&Version=1.0.0&MAP=france_parts'
            '&DATAINPUTS=INPUT=france_parts%3BOUTPUT=france_parts_2'
        )
        rv = self.client.get(uri, headers={'X-Lizmap-User-Groups': 'operator,admin'})
        assert rv.status_code == 403

    def test_getcapabilities_1(self):
        """ Test Lizmap access policy
        """
        uri = ('?service=WPS&request=GetCapabilities')
        rv = self.client.get(uri, headers={'X-Lizmap-User-Groups': 'operator,admin'})
        assert rv.status_code == 200

        exposed = rv.xpath_text(
            '/wps:Capabilities'
            '/wps:ProcessOfferings'
            '/wps:Process'
            '/ows:Identifier',
        ).split()
        # Test that only  scripts are exposed
        assert all(p.startswith('script:') for p in exposed)

    def test_getcapabilities_2(self):
        """ Test Lizmap access policy
        """
        uri = ('?service=WPS&request=GetCapabilities&MAP=france_parts')
        rv = self.client.get(uri, headers={'X-Lizmap-User-Groups': 'operator,admin'})
        assert rv.status_code == 200

        exposed = rv.xpath_text(
            '/wps:Capabilities'
            '/wps:ProcessOfferings'
            '/wps:Process'
            '/ows:Identifier',
        )
        # Check that there is only one exposed pyqgiswps_test
        idents = [x for x in exposed.split() if x.startswith('pyqgiswps_test:')]
        assert idents == ['pyqgiswps_test:testsimplevalue']

    def test_getcapabilities_3(self):
        """ Test Lizmap access policy
        """
        uri = ('?service=WPS&request=GetCapabilities&MAP=france_parts')
        rv = self.client.get(uri, headers={'X-Lizmap-User': 'john'})
        assert rv.status_code == 200

        exposed = rv.xpath_text(
            '/wps:Capabilities'
            '/wps:ProcessOfferings'
            '/wps:Process'
            '/ows:Identifier',
        )
        # Check that there is only one exposed pyqgiswps_test
        idents = [x for x in exposed.split() if x.startswith('pyqgiswps_test:')]
        assert idents == ['pyqgiswps_test:testcopylayer']

    def test_execute_return_ok(self):
        """ Test map profile
        """
        uri = (
            '?service=WPS'
            '&request=Execute'
            '&Identifier=pyqgiswps_test:testcopylayer'
            '&Version=1.0.0'
            '&MAP=france_parts'
            '&DATAINPUTS=INPUT=france_parts%3BOUTPUT=france_parts_2'
        )
        rv = self.client.get(uri, headers={'X-Lizmap-User': 'john'})
        assert rv.status_code == 200

    def test_subfolder_map(self):
        """ Test Lizmap access policy
        """
        uri = ('?service=WPS&request=GetCapabilities&MAP=others/france_parts')
        rv = self.client.get(uri, headers={'X-Lizmap-User': 'jack'})
        assert rv.status_code == 200

        exposed = rv.xpath_text(
            '/wps:Capabilities'
            '/wps:ProcessOfferings'
            '/wps:Process'
            '/ows:Identifier',
        )
        # Check that there is only one exposed pyqgiswps_test
        idents = [x for x in exposed.split() if x.startswith('pyqgiswps_test:')]
        assert idents == ['pyqgiswps_test:testcopylayer']

    def test_encoded_url(self):
        """ Test Lizmap access policy
        """
        uri = ('?service=WPS&request=GetCapabilities&MAP=others%2Ffrance_parts')
        rv = self.client.get(uri, headers={'X-Lizmap-User': 'jack'})
        assert rv.status_code == 200

        exposed = rv.xpath_text(
            '/wps:Capabilities'
            '/wps:ProcessOfferings'
            '/wps:Process'
            '/ows:Identifier',
        )
        # Check that there is only one exposed pyqgiswps_test
        idents = [x for x in exposed.split() if x.startswith('pyqgiswps_test:')]
        assert idents == ['pyqgiswps_test:testcopylayer']
