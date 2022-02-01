# vim: ft=dockerfile
ARG REGISTRY_PREFIX=''
ARG QGIS_VERSION=release

FROM  ${REGISTRY_PREFIX}qgis-platform:${QGIS_VERSION}
MAINTAINER David Marteau <david.marteau@3liz.com>
LABEL Description="QGIS3 WPS service" Vendor="3liz.org" Version="1."

ARG PIP_OPTIONS
ARG BUILD_VERSION

RUN apt-get update && apt-get install -y --no-install-recommends gosu \
     python3-shapely  \
     python3-psutil \
     && apt-get clean  && rm -rf /var/lib/apt/lists/* \
     && rm -rf /usr/share/man 

# Create virtualenv for installing server
RUN mkdir -p /opt/local/ \ 
    && python3 -m venv --system-site-packages /opt/local/pyqgiswps && cd /usr/local/bin \
    && /opt/local/pyqgiswps/bin/pip install -U --no-cache-dir pip setuptools wheel \
    && /opt/local/pyqgiswps/bin/pip install --no-cache-dir \
        plotly \
        simplejson \
        geojson \
        scipy  \
        pandas \
        Jinja2 \
    && /opt/local/pyqgiswps/bin/pip install --no-cache-dir $PIP_OPTIONS   \
        "py-qgis-wps==${BUILD_VERSION}" \
        "pyqgiservercontrib-lizmap-access-policy" \
    && ln -s /opt/local/servicemngr/bin/wpsserver \
    && ln -s /opt/local/servicemngr/bin/wpsserver-check \
    && rm -rf /root/.cache /root/.ccache

COPY /docker-entrypoint.sh /
RUN chmod 0755 /docker-entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]


