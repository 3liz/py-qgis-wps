import asyncio

import tornado.platform.asyncio
import tornado.httpclient

from tornado.platform.asyncio import to_asyncio_future
from time import time

async def worker( wid, throttle, count, url, **kwargs ):
    for n in range(count):
        t = time()
        resp = await to_asyncio_future(tornado.httpclient.AsyncHTTPClient().fetch( url, raise_error=False, **kwargs ));
        t = time()-t
        print('[%d] %s - %s' % (wid, resp.code, int(t*1000) ))
        await asyncio.sleep(throttle)
    print("worker", wid, "done")

post_data = open('testcopylayer.xml').read()

def get_request( project, storeExecuteResponse ):
    return dict( url=("http://localhost:8080/?SERVICE=WPS&Request=Execute&Identifier=lzmtest:testcopylayer&Version=1.0.0"
                       "&MAP=france_parts&DATAINPUTS=INPUT={project};OUTPUT=copy_of_layer"
                       "&storeExecuteResponse={storeExecuteResponse}").format(project=project,
                           storeExecuteResponse='true' if storeExecuteResponse else 'false') )

def post_request( project, layer, storeExecuteResponse ):
    return dict( url="http://localhost:8080/?SERVICE=WPS&MAP={}".format(project),
                 method  = 'POST',
                 headers = { "Content-Type": "text/xml" },
                 body    = post_data.format(storeExecuteResponse='true' if storeExecuteResponse else 'false', layer=layer)
        ) 

num_workers = 4
throttle=0
count=25

tornado.platform.asyncio.AsyncIOMainLoop().install()

#workers = [ worker( i+1, throttle, count, **post_request( 'montpellier/montpellier.qgs', 'france_parts',  False ) ) for i in range(num_workers)]
workers = [ worker( i+1, throttle, count, **post_request( 'montpellier/montpellier.qgs', 'Quartiers', True ) ) for i in range(num_workers)]

dt = time()
loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(*workers))
loop.close()
print("Elapsed:", int((time()-dt)*1000))

