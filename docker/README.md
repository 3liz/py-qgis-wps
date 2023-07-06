# QGIS WPS Docker image

Setup a Docker image for running Py-Qgis-WPS

## Running the service

The following document assumes that your are somehow familiar with the basics of [Docker](https://docs.docker.com/).

Unless you already have a Redis service running you have to create one:
```
# Create a bridge network
docker network create mynet
# Run redis on background on that network
docker run -d --rm --name redis --net mynet redis:4 
```

And launch the service interactively on the port 8080 on the same network

```
docker run -it --rm -p 127.0.0.1:8080:8080 --net mynet \
       -v /path/to/processing/:/processing \
       -v /path/to/qgis/projects:/projects \
       -v /path/to/processing/output/dir:/srv/data \
       -e QGSWPS_SERVER_WORKDIR=/srv/data \
       -e QGSWPS_SERVER_PARALLELPROCESSES=2 \
       -e QGSWPS_SERVER_LOGSTORAGE=REDIS \
       -e QGSWPS_PROCESSING_PROVIDERS=provider1,provider2  \
       -e QGSWPS_PROCESSING_PROVIDERS_MODULE_PATH=/processing \
       -e QGSWPS_CACHE_ROOTDIR=/projects \
       -e QGSWPS_USER={uid}:{gid} \
       3liz/qgis-wps
```

Replace {uid}:{gid} by the approriate uid and gid of your mounted volume directories. Alternatively you may use the
`-u <uid>` Docker options to set the appropriates rights.

*Note*: This will run the service interactively on your terminal, on a production environment you will have 
to adapt the deployment according to your infrastructure.


Alternatively, you may use [docker-compose](https://docs.docker.com/compose/) for launching the service

## Setting master projects

Master QGIS projects must be located at the location given by  `QGSWPS_CACHE_ROOTDIR` - see configuration variables.

Processing algorithms are located at the location given by `QGSWPS_PROCESSING_PROVIDERS_MODULE_PATH`.
See the [py-qgis-wps](https://py-qgis-wps.readthedocs.io/en/latest/qgisprocessing.html#exposing-processing-algorithms) on how to configure properly you provider directory.

## Configuration 

Configuration is done with environment variables 

### Global server configuration (from the qywps documentation):

- QGSWPS\_SERVER\_WORKDIR: set the current dir processes, all processes will be running in that directory.
- QGSWPS\_SERVER\_HOST\_PROXY: When the service is behind a reverse proxy, set this to the proxy entrypoint.
- QGSWPS\_SERVER\_PARALLELPROCESSES: Number of parallel process workers
- QGSWPS\_SERVER\_RESPONSE\_TIMEOUT: The max response time before killing a process.
- QGSWPS\_SERVER\_RESPONSE\_EXPIRATION: The max time (in seconds) the response from a WPS process will be available.
- QGSWPS\_SERVER\_WMS\_SERVICE\_URL: The base url for WMS service. Default to <hosturl>/wms. Responses from processing will
be returned as WMS urls. This configuration variable sets the base url for accessing results.
- QGSWPS\_SERVER\_RESULTS\_MAP\_URI

#### Logging

- QGSWPS\_LOGLEVEL: the log level, should be `INFO` in production mode, `DEBUG` for debug output. 

#### REDIS logstorage configuration

- QGSWPS\_REDIS\_HOST: The redis host
- QGSWPS\_REDIS\_PORT: The redis port. Default to 6379
- QGSWPS\_REDIS\_DBNUM: The redis database number used. Default to 0


#### QGIS project Cache configuration

- QGSWPS\_CACHE\_ROOTDIR: Absolute path to the qgis projects root directory, projects referenges with the MAP parameter will be searched at this location

#### Processing configuration

- QGSWPS\_PROCESSING\_PROVIDERS: List of providers for publishing algorithms (comma separated)
- QGSWPS\_PROCESSING\_PROVIDERS\_MODULE\_PATH: Path to look for processing algoritms provider to publish, algorithms from providers specified heres will be runnable as WPS processes.


## Using with Lizmap

For using with Lizmap,  you need to adjust the lizmap configuration with the following:

### Configuring the wps support in Lizmap

You must add the WPS support by adding the following in your *localconfig.ini* file:

```
[modules]
wps.access=2

[wps]
wps_url=http://locahost:8080/ows/
# Base URL to your WMS service (WPS/Processing results are returned as WMS urls.
ows_url=<url to WMS>
# Set the base for the qgis master projects, lizmap will use relative MAP path from this value
wps_rootDirectories="/srv/projects"
redis_host=redis 
redis_port=6379
redis_db=1
redis_key_prefix=wpslizmap

```

You must  set the master project directory `QGSWPS_CACHE_ROOTDIR` to the same location as the qgis lizmap
projects directory (Lizmap projects directory). Which corresponds to `/srv/projects` in our project.
