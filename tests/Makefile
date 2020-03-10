SHELL:=bash
#
#  Makefile for running server in docker containers
#
COMMITID=$(shell git rev-parse --short HEAD)

REGISTRY_URL ?= 3liz
REGISTRY_PREFIX=$(REGISTRY_URL)/

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
	rm -rf unittests/__outputdir__/*
	docker run --rm --name qgis-wps-test-$(FLAVOR)-$(COMMITID) -w /src \
    -u $(BECOME_USER) \
    -v $(SRCDIR):/src \
    -v $$(pwd)/.local:/.local \
    -v $(LOCAL_HOME)/.cache:/.cache \
    -e FAKEREDIS=yes \
    -e PIP_CACHE_DIR=/.cache \
    -e PYTEST_ADDOPTS="$(PYTEST_ADDOPTS)" \
    -e QGSWPS_CACHE_ROOTDIR=/src/tests/unittests/data \
    -e QGSWPS_PROCESSING_PROVIDERS_MODULE_PATH=/src/tests/unittests \
    -e QGIS_OPTIONS_PATH=/src/tests/qgis \
    $(QGIS_IMAGE) /src/tests/run-tests.sh


WORKERS:=1

stop:
	docker-compose stop  || true
	docker-compose rm -f || true

run: stop local
	mkdir -p $$(pwd)/__workdir__
	export BECOME_USER=$(BECOME_USER)  \
    QGIS_IMAGE=$(QGIS_IMAGE) \
    WORKERS=$(WORKERS) \
    LOCAL_HOME=$(LOCAL_HOME) \
    SRCDIR=$(SRCDIR) \
    PYTEST_ADDOPTS="$(PYTEST_ADDOPTS)" \
    RUN_COMMAND=/src/tests/run-server.sh \
    && docker-compose up     

# Run tests with real redis to test asynchronous
# behavior  
test-async: stop local
	rm -rf unittests/__outputdir__/*
	export BECOME_USER=$(BECOME_USER)  \
    QGIS_IMAGE=$(QGIS_IMAGE) \
    WORKERS=$(WORKERS) \
    LOCAL_HOME=$(LOCAL_HOME) \
    SRCDIR=$(SRCDIR) \
    PYTEST_ADDOPTS="$(PYTEST_ADDOPTS)" \
    RUN_COMMAND=/src/tests/run-tests.sh \
    && docker-compose up     


test-pool: local
	docker run --rm --name qgis-wps-test-pool-$(FLAVOR)-$(COMMITID) -w /src \
    -u $(BECOME_USER) \
    -v $(SRCDIR):/src \
    -v $$(pwd)/.local:/.local \
    -v $(LOCAL_HOME)/.cache:/.cache \
    -e PIP_CACHE_DIR=/.cache \
    -e PYTEST_ADDOPTS="$(PYTEST_ADDOPTS)" \
    $(QGIS_IMAGE) /src/tests/run-pool-tests.sh

