##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import lxml.etree
from pyqgiswps.app import WPSRequest
import tempfile


class TestWPSRequest:

    def setup_method(self, me):

        self.tempfile = tempfile.mktemp()

        x = open(self.tempfile, 'w')
        x.write("ahoj")
        x.close()


    def test_json_in(self):

        obj = {
            'operation': 'getcapabilities',
            'version': '1.0.0',
            'language': 'eng',
            'identifiers': 'ahoj',
            'store_execute': True,
            'status': True,
            'lineage': True,
            'inputs': {
                'myin': [{
                    'identifier': 'myin',
                    'type': 'complex',
                    'supported_formats': [{
                        'mime_type': 'tralala'
                    }],
                    'file': self.tempfile,
                    'data_format': {'mime_type': 'tralala'}
                }],
                'myliteral': [{
                    'identifier': 'myliteral',
                    'type': 'literal',
                    'data_type': 'integer',
                    'allowed_values': [ {'type':'anyvalue'} ],
                    'data': 1
                }]
            },
            'outputs': {},
            'raw': False
        }

        request = WPSRequest()
        request.json = obj

        assert request.inputs['myliteral'][0].data == 1, 'Data are in the file'
        assert request.inputs['myin'][0].data == 'ahoj', 'Data are in the file'
        assert request.inputs['myliteral'][0].allowed_values == [], 'Any value set'
        assert request.inputs['myliteral'][0].any_value, 'Any value set'


