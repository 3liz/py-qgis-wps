
from qywps.app.Common import Metadata
from qywps.inout.formats import Format
from qywps.inout import (LiteralInput,
                        ComplexInput,
                        BoundingBoxInput,
                        LiteralOutput,
                        ComplexOutput,
                        BoundingBoxOutput)

from qywps import WPS, OWS

def test_complex_output_href():
    """ Test external reference in complex output 
    """

    kwargs = {
        'identifier': 'hreftest' ,
        'title'     : '',
        'abstract'  : '',
    }

    output = ComplexOutput(supported_formats=[
                        Format("application/x-ogc-wms"),
                        Format("application/x-ogc-wfs")
                    ], as_reference=True, **kwargs)

    output.output_format = "application/x-ogc-wms"
    output.url = "http://my.org/external/ref"

    output_elements = output.execute_xml()

    # Check that <wps:Reference href=...> is not namspaced
    element =  output_elements.xpath('//wps:Reference', namespaces={'wps': "http://www.opengis.net/wps/1.0.0"})

    assert len(element) == 1
    assert 'href' in element[0].attrib

