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
from pyqgiswps.app import WPSProcess
from pyqgiswps.inout import (Format,
                             BoundingBoxOutput, 
                             BoundingBoxInput, 
                             ComplexInput, 
                             ComplexOutput, 
                             LiteralOutput,
                             LiteralInput)
from pyqgiswps.validator.base import emptyvalidator
from pyqgiswps.validator.complexvalidator import validategml
from pyqgiswps.exceptions import InvalidParameterValue

from pyqgiswps.ogc.api.request import get_inputs_from_document, get_outputs_from_document

#
# Tests for execution request json parser
#

def test_empty():
    request_doc = {}
    assert get_inputs_from_document(request_doc) == {}


def test_multiple_raw_input():
    request_doc = {
        'inputs': {
            'name': [ 'foo', 'bar' ],
        }
    }
    rv = get_inputs_from_document(request_doc)
    assert 'name' in rv
    assert isinstance(rv['name'], list)
    assert len(rv['name']) == 2
    assert rv['name'][0]['data'] == 'foo'
    assert rv['name'][1]['data'] == 'bar'


def test_multiple_qualified_input():
    request_doc = {
        'inputs': {
            'name': [ 
                { 'value': 'foo' }, 
                { 'value': 'bar' }
            ],
        }
    }
    rv = get_inputs_from_document(request_doc)
    assert 'name' in rv
    inpt = rv['name']
    assert isinstance(inpt, list)
    assert len(inpt) == 2
 
    assert inpt[0]['data'] == 'foo'
    assert inpt[1]['data'] == 'bar'


def test_two_raw_inputs():
    request_doc = {
        'inputs': {
            'name1': 'foo',
            'name2': 'bar',
        }
    }
    rv = get_inputs_from_document(request_doc)
    assert rv['name1'][0]['data'] == 'foo'
    assert rv['name2'][0]['data'] == 'bar'


def test_complex_string_input():
    the_data = "hello world"
    request_doc = {
        'inputs': {
            'name': {
                'value': the_data,
                'mediaType': 'text/foobar'
            }
        }
    }
    rv = get_inputs_from_document(request_doc)
    inpt = rv['name']
    assert isinstance(inpt, list)
    assert len(inpt) == 1
 
    assert inpt[0]['mimeType'] == 'text/foobar'
    assert inpt[0]['data'] == 'hello world'


def test_complex_input_json_value():
    the_data = '{ "plot":{ "Version" : "0.1" } }'
    request_doc = {
        'inputs': {
            'json': {
                'value': the_data,
                'mediaType': 'application/json',
            }
        }
    }
    rv = get_inputs_from_document(request_doc)
    inpt = rv['json']
    assert isinstance(inpt, list)
    assert len(inpt) == 1
 
    assert inpt[0]['mimeType'] == 'application/json'
    json_data = json.loads(inpt[0]['data'])
    assert json_data['plot']['Version'] == '0.1'


def test_complex_input_base64_value():
    the_data = 'eyAicGxvdCI6eyAiVmVyc2lvbiIgOiAiMC4xIiB9IH0='

    request_doc = {
        'inputs': {
            'json': {
                'value': the_data,
                'encoding': 'base64',
                'mediaType': 'application/json',
            }
        }
    }
 
    rv = get_inputs_from_document(request_doc)
    inpt = rv['json']
    assert isinstance(inpt, list)
    assert len(inpt) == 1
    assert inpt[0]['mimeType'] == 'application/json'
    json_data = json.loads(inpt[0]['data'].decode())
    assert json_data['plot']['Version'] == '0.1'


def test_bbox_input():
    bbox = [40.0, 50.0, 60.0, 70.0]
    request_doc = {
        'inputs': {
            'mybbox': {
                'bbox': bbox,
            },
        },
    }
    rv = get_inputs_from_document(request_doc)
    inpt = rv['mybbox']
    assert isinstance(inpt, list)
    assert len(inpt) == 1
    assert isinstance(inpt[0],dict)
    assert inpt[0]['data'] == bbox


def test_reference_post_input():
    request_doc = {
        'inputs': {
            'name': {
                'href': 'http://foo/bar/service',
                'type': "text/xml",
                'method': "POST",
                'body': 'request body'
            }
        }
    }

    rv = get_inputs_from_document(request_doc)
    inpt = rv['name']
    assert len(inpt) == 1
    assert isinstance(inpt[0],dict)
    assert inpt[0]['href'] == 'http://foo/bar/service'
    assert inpt[0]['method'] == 'POST'
    assert inpt[0]['body'] == 'request body'

