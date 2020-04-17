# Need docker above v17-05.0-ce
ARG REGISTRY_PREFIX=''
ARG QGIS_VERSION=latest

FROM  ${REGISTRY_PREFIX}qgis-platform:${QGIS_VERSION}
MAINTAINER David Marteau <david.marteau@3liz.com>
LABEL Description="QGIS3 WPS service" Vendor="3liz.org" Version="1."

ARG BUILD_VERSION

RUN pip3 install \
    scipy \
    simplejson \
    geojson \
    pandas \
    && rm -rf /root/.cache /root/.ccache

COPY docker-entrypoint.sh /
RUN  chmod 0755 /docker-entrypoint.sh

COPY dist/py-qgis-wps-$BUILD_VERSION.tar.gz /
RUN pip3 install --no-cache-dir /py-qgis-wps-$BUILD_VERSION.tar.gz

# && rm -rf /root/.cache /root/.ccache

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]


