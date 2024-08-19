import lxml.etree

NAMESPACES = {
    'xlink': "http://www.w3.org/1999/xlink",
    'wps': "http://www.opengis.net/wps/1.0.0",
    'ows': "http://www.opengis.net/ows/1.1",
    'gml': "http://www.opengis.net/gml",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
}


class Response:

    def __init__(self, http_response):
        self.http_response = http_response
        if self.headers.get('Content-Type', '').find('text/xml') == 0:
            self.xml = lxml.etree.fromstring(http_response.content)

    @property
    def status_code(self):
        return self.http_response.status_code

    @property
    def headers(self):
        return self.http_response.headers

    def xpath(self, path):
        return self.xml.xpath(path, namespaces=NAMESPACES)

    def xpath_attr(self, path, attribut):
        return self.xpath(path)[0].attrib[attribut]

    def xpath_text(self, path):
        return ' '.join(e.text for e in self.xpath(path))


def assert_response_accepted(resp):
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'
    success = resp.xpath_text('/wps:ExecuteResponse'
                              '/wps:Status'
                              '/wps:ProcessAccepted')
    assert success is not None
    # TODO: assert status URL is present


def assert_process_started(resp):
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'
    success = resp.xpath_text('/wps:ExecuteResponse'
                              '/wps:Status'
                              'ProcessStarted')
    # Is it still like this in PyWPS-4 ?
    assert success.split[0] == "processstarted"


def assert_response_success(resp):
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'text/xml;charset=utf-8'
    success = resp.xpath('/wps:ExecuteResponse/wps:Status/wps:ProcessSucceeded')
    assert len(success) == 1


def assert_qywps_version(resp, version):
    # get first child of root element
    root_firstchild = resp.xpath('/*')[0].getprevious()
    assert isinstance(root_firstchild, lxml.etree._Comment)
    tokens = root_firstchild.text.split()
    assert len(tokens) == 2
    assert tokens[0] == 'QyWPS'
    assert tokens[1] == version
