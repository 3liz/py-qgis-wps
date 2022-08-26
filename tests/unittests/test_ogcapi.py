#
# Copyright 2022 3liz
# Author: David Marteau
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#


import asyncio
import lxml.etree
import json

from urllib.parse import urlparse

from pyqgiswps.app import WPSProcess
from pyqgiswps.inout import (Format,
                             BoundingBoxOutput, 
                             BoundingBoxInput, 
                             ComplexInput, 
                             ComplexOutput, 
                             LiteralOutput,
                             LiteralInput)
from pyqgiswps.validator.base import emptyvalidator
from pyqgiswps.exceptions import InvalidParameterValue

from pyqgiswps.tests import HTTPTestCase, HttpClient

from test_common import async_test

#
# HTTP tests
#
# XXX handler function *MUST* be accessible from execution context and only module
# in top level are accessible when running tests
#


def ultimate_question(request, response):
    response.outputs['outvalue'].data = 42
    return response


def create_ultimate_question():

    return WPSProcess(handler=ultimate_question,
                   identifier='ultimate_question',
                   title='Ultimate Question',
                   outputs=[LiteralOutput('outvalue', 'Output Value', data_type='integer')])


def greeter(request, response):
    name = request.inputs['name'][0].data
    assert type(name) is str
    response.outputs['message'].data = "Hello %s!" % name
    return response


def create_greeter():
    return WPSProcess(handler=greeter,
                   identifier='greeter',
                   title='Greeter',
                   inputs=[LiteralInput('name', 'Input name', data_type='string')],
                   outputs=[LiteralOutput('message', 'Output message', data_type='string')])


def bbox_process(request, response):
    coords = request.inputs['mybbox'][0].data
    assert type(coords) == type([])
    assert len(coords) == 4
    assert coords[0] == float(15)
    response.outputs['outbbox'].data = coords
    return response


def create_bbox_process():
    return WPSProcess(handler=bbox_process,
                   identifier='my_bbox_process',
                   title='Bbox process',
                   inputs=[BoundingBoxInput('mybbox', 'Input name', ["EPSG:4326"])],
                   outputs=[BoundingBoxOutput('outbbox', 'Output message', ["EPSG:4326"])])

def complex_process(request, response):
    response.outputs['complex'].data = request.inputs['complex'][0].data
    return response


def create_complex_process():
    frmt = Format(mime_type='application/gml') # this is unknown mimetype

    return WPSProcess(handler=complex_process,
            identifier='my_complex_process',
            title='Complex process',
            inputs=[
                ComplexInput(
                    'complex',
                    'Complex input',
                    supported_formats=[frmt])
            ],
            outputs=[
                ComplexOutput(
                    'complex',
                    'Complex output',
                    supported_formats=[frmt])
             ])


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
        return [
            create_ultimate_question(),
            create_greeter(),
            create_bbox_process(),
        ]

   
    def test_execution_with_no_inputs(self):
        request_doc = {}
        resp = self.client.post_json('/processes/ultimate_question/execution', data=request_doc)
        doc = assert_response_success(resp)
        assert doc['outvalue'] ==  42

    def test_post_with_string_input(self):
        request_doc = {
           'inputs': {
               'name': 'foo'
            }      
        }
        resp = self.client.post_json("/processes/greeter/execution", request_doc)
        doc = assert_response_success(resp)
        assert doc['message'] ==  "Hello foo!"

    def test_bbox_input_no_crs(self):
        request_doc = {
            'inputs': {
                'mybbox': {
                    'bbox': [15.0, 50.0, 16.0, 51.0],
                }    
            }
        }
        resp = self.client.post_json("/processes/my_bbox_process/execution", request_doc)
        doc = assert_response_success(resp)

        output = doc['outbbox']
        assert output['bbox'][0] == 15.0
        assert output['bbox'][1] == 50.0
