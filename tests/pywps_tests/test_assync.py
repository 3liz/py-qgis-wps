##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import unittest
import time
from qywps import Service, Process, LiteralInput, LiteralOutput
from qywps import WPS, OWS
from qywps.tests import HTTPTestCase, assert_response_accepted


def create_sleep():

    def sleep(request, response):
        seconds = request.inputs['seconds']
        assert type(seconds) is type(1.0)

        step = seconds / 10
        for i in range(10):
            # How is status working in version 4 ?
            #self.status.set("Waiting...", i * 10)
            time.sleep(step)

        response.outputs['finished'] = "True"
        return response

    return Process(handler=sleep,
                   identifier='sleep',
                   title='Sleep',
                   inputs=[
                       LiteralInput('seconds', title='Seconds', data_type='float')
                   ],
                   outputs=[
                       LiteralOutput('finished', title='Finished', data_type='boolean')
                   ]
    )


class ExecuteTest(HTTPTestCase):

    def test_assync(self):
        client = self.client_for(Service(processes=[create_sleep()]))
        request_doc = WPS.Execute(
            OWS.Identifier('sleep'),
            WPS.DataInputs(
                WPS.Input(
                    OWS.Identifier('seconds'),
                    WPS.Data(
                        WPS.LiteralData(
                            "120"
                        )
                    )
                )
            ),
            version="1.0.0"
        )
        resp = client.post_xml(doc=request_doc)
        assert_response_accepted(resp)

        # TODO:
        # . extract the status URL from the response
        # . send a status request
