# vim: ft=dockerfile
ARG REGISTRY_PREFIX=''
ARG QGIS_VERSION=release

FROM  ${REGISTRY_PREFIX}qgis-platform:${QGIS_VERSION}
LABEL Description="QGIS3 WPS service" Vendor="3liz.org" Version="1."
LABEL Maintainer="David Marteau <david.marteau@3liz.com>"

ARG PIP_OPTIONS
ARG BUILD_VERSION

RUN apt-get update && apt-get install -y --no-install-recommends gosu \
     python3-shapely  \
     python3-psutil \
     && apt-get clean  && rm -rf /var/lib/apt/lists/* \
     && rm -rf /usr/share/man 

# Create virtualenv for installing server
RUN mkdir -p /opt/local/ \
    && python3 -m venv --system-site-packages /opt/local/pyqgiswps \
    && cd /usr/local/bin \
    && /opt/local/pyqgiswps/bin/pip install -U --upgrade-strategy=eager \
       --no-cache-dir pip setuptools wheel packaging>=22.0 \
    && /opt/local/pyqgiswps/bin/pip install -U --upgrade-strategy=eager \
        --no-cache-dir \
        plotly \
        simplejson \
        geojson \
        scipy  \
        pandas \
        Jinja2 \
    ${NULL}

COPY pyqgiswps py-qgis-wps/pyqgiswps
COPY pyqgisservercontrib py-qgis-wps/pyqgisservercontrib
COPY setup.py pyproject.toml VERSION py-qgis-wps/

# Create virtualenv for installing server
RUN mkdir -p /opt/local/ \
    && python3 -m venv --system-site-packages /opt/local/pyqgiswps \
    && cd /usr/local/bin \
    && /opt/local/pyqgiswps/bin/pip install -U --no-cache-dir pip setuptools wheel \
    && /opt/local/pyqgiswps/bin/pip install --no-cache-dir \
        -e /py-qgis-wps \
    && ln -s /opt/local/pyqgiswps/bin/wpsserver \
    && ln -s /opt/local/pyqgiswps/bin/wpsserver-check \
    ${NULL}

COPY docker/docker-entrypoint.sh /
RUN chmod 0755 /docker-entrypoint.sh

# Expose to all interfaces in container
ENV QGSWPS_SERVER_INTERFACES=0.0.0.0

EXPOSE 8080

ENTRYPOINT ["/docker-entrypoint.sh"]

