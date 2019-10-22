SHELL:=bash
#
#  Makefile for running server in docker containers
#
COMMITID=$(shell git rev-parse --short HEAD)

ifdef REGISTRY_URL
REGISTRY_PREFIX=$(REGISTRY_URL)/
endif

FLAVOR:=ltr

QGIS_IMAGE:=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)

# Define a pip conf to use
#
BECOME_USER:=$(shell id -u)

SERVER_HTTP_PORT:=127.0.0.1:8888

ifndef LOCAL_HOME
LOCAL_HOME=$(shell pwd)
endif

SRCDIR=$(shell realpath ..)

local:
	rm -rf $$(pwd)/.local/share
	mkdir -p  $$(pwd)/.local  $(LOCAL_HOME)/.cache

test: local
	docker run --rm --name qgis-wps-test-$(FLAVOR)-$(COMMITID) -w /src \
    -u $(BECOME_USER) \
    -v $(SRCDIR):/src \
    -v $$(pwd)/.local:/.local \
    -v $(LOCAL_HOME)/.cache:/.cache \
    -e PIP_CACHE_DIR=/.cache \
    -e PYTEST_ADDOPTS="$(PYTEST_ADDOPTS)" \
    -e QYWPS_CACHE_ROOTDIR=/src/tests/unittests/data \
    -e QGIS_OPTIONS_PATH=/src/tests/qgis \
    $(QGIS_IMAGE) /src/tests/run-tests.sh


WORKERS:=1

run: local
	mkdir -p $$(pwd)/__workdir__
	docker run -it --rm --name qgis-wps-run-$(FLAVOR)-$(COMMITID) -w /src \
    -u $(BECOME_USER) \
    -v $(SRCDIR):/src \
    -v $$(pwd)/.local:/.local \
    -v $(LOCAL_HOME)/.cache:/.cache \
    -v $$(pwd)/__workdir__:/srv/data \
    -e PIP_CACHE_DIR=/.cache \
    -e WORKERS=$(WORKERS) \
    -e QYWPS_CACHE_ROOTDIR=/src/tests/unittests/data \
    -e QYWPS_PROCESSING_PROVIDERS_MODULE_PATH=/src/tests/unittests \
    -e QYWPS_SERVER_WORKDIR=/srv/data \
    -e QGIS_OPTIONS_PATH=/src/tests/qgis \
    -p $(SERVER_HTTP_PORT):8080 \
    $(QGIS_IMAGE) /src/tests/run-server.sh

