#
# Copyright 2022 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


from urllib.parse import urlparse

from test_common import async_test

from pyqgiswps.executors.processfactory import get_process_factory
from pyqgiswps.tests import HttpClient, HTTPTestCase

#
# HTTP tests
#
# XXX handler function *MUST* be accessible from execution context and only module
# in top level are accessible when running tests
#


def assert_response_success(resp, code=200):
    assert resp.status_code == code
    assert resp.headers.get('Content-Type') == "application/json;charset=utf-8"
    return resp.json


class ApiTestCase(HTTPTestCase):
    @property
    def client(self):
        """ Override """
        return HttpClient(self)


class ExecuteTest(ApiTestCase):

    def get_processes(self):
        return get_process_factory()._create_qgis_processes()

    def test_ogcapi_execute_sync(self):
        """ Test sync running
        """
        identifier = "pyqgiswps_test:testcopylayer"

        rv = self.client.post_json(
            f"/processes/{identifier}/execution?MAP=france_parts",
            {
                'inputs': {
                    'INPUT': 'france_parts',
                    'OUTPUT': 'france_parts_2',
                },
            },
        )

        resp = assert_response_success(rv, code=200)

        # We must have the full response
        output = resp.get('OUTPUT')
        assert output is not None
        assert output.get('type') == 'application/x-ogc-wms'
        assert output.get('href') is not None

        job_id = rv.headers.get('X-Job-Id')
        assert job_id is not None

        status_path = f"/jobs/{job_id}"

        # Retrieve the status
        rv = self.client.get(status_path)
        resp = assert_response_success(rv)

        assert resp.get('status') == 'successful'

    @async_test
    def test_ogcapi_execute_async(self):
        """ Test status location
        """
        identifier = "pyqgiswps_test:testcopylayer"

        rv = self.client.post_json(
            f"/processes/{identifier}/execution?MAP=france_parts",
            {
                'inputs': {
                    'INPUT': 'france_parts',
                    'OUTPUT': 'france_parts_2',
                },
            },
            headers={'Prefer': 'respond-async'},
        )

        resp = assert_response_success(rv, code=201)
        assert resp.get('status') == 'accepted'
        assert resp.get('processID') == identifier

        job_id = resp.get('jobID')
        assert job_id is not None

        location = rv.headers.get('Location')
        assert location is not None

        pref_applied = rv.headers.get('Preference-Applied')
        assert pref_applied is not None
        assert pref_applied == "respond-async"

        expected_status_path = f"/jobs/{job_id}"

        loc_url = urlparse(location)
        assert loc_url.path == expected_status_path

        # Retrieve the status
        rv = self.client.get(expected_status_path)
        assert_response_success(rv)
