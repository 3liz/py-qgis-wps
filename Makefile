.PHONY: tests
# 
# qypws makefile
#

BUILDID=$(shell date +"%Y%m%d%H%M")
COMMITID=$(shell git rev-parse --short HEAD)

BUILDDIR=build
DIST=${BUILDDIR}/dist

MANIFEST=factory.manifest

PYTHON:=python3

ifdef REGISTRY_URL
REGISTRY_PREFIX=$(REGISTRY_URL)/
endif

FLAVOR:=ltr

QGIS_IMAGE:=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)

dirs:
	mkdir -p $(DIST)

manifest:
	echo name=$(shell $(PYTHON) setup.py --name) > $(MANIFEST) && \
    echo version=$(shell $(PYTHON) setup.py --version) >> $(MANIFEST) && \
    echo buildid=$(BUILDID)   >> $(MANIFEST) && \
    echo commitid=$(COMMITID) >> $(MANIFEST)

# Define a pip conf to use
#
PIP_CONFIG_FILE:=pip.conf
BECOME_USER:=$(shell id -u)

ifndef LOCAL_HOME
LOCAL_HOME=$(shell pwd)
endif

local:
	rm -rf $$(pwd)/.local/share
	mkdir -p  $$(pwd)/.local  $(LOCAL_HOME)/.ccache $(LOCAL_HOME)/.cache

test: local
	docker run --rm --name qgis-wps-test-$(FLAVOR)-$(COMMITID) -w /src \
    -u $(BECOME_USER) \
    -v $$(pwd):/src \
    -v $$(pwd)/.local:/.local \
    -v $(LOCAL_HOME)/.cache:/.cache \
    -v $(LOCAL_HOME)/.ccache:/.ccache \
    -e PIP_CACHE_DIR=/.cache \
    $(QGIS_IMAGE) /src/run_tests.sh


# Build dependencies
deps: dirs
	pip wheel -w $(DIST) -r requirements.txt

wheel: deps
	mkdir -p $(DIST)
	$(PYTHON) setup.py bdist_wheel --dist-dir=$(DIST)

deliver:
	twine upload -r storage $(DIST)/*

dist: dirs manifest
	$(PYTHON) setup.py sdist --dist-dir=$(DIST)

clean:
	rm -rf $(BUILDDIR)


LOCAL_PORT:=127.0.0.1:8080

LOGSTORAGE:=REDIS
REDIS_HOST:=redis
DOCKER_OPTIONS:= --net mynet
PROCESSING:=$(shell pwd)/run-tests
PROVIDERS:=lzmtest

# Install in  develop mode in a docker

WORKERS:=2

# Run redis as
# docker run -it --rm --name redis --net mynet redis:<version>

run: local
	@echo "Do not forget to run 'docker run -it --rm -p 6379:6379 --name redis --net mynet redis:<version>'"
	mkdir -p $$(pwd)/run-tests/__workdir__
	docker run -it --rm -p $(LOCAL_PORT):8080 --name qgis3-wps-run-$(COMMITID) $(DOCKER_OPTIONS) -w /src \
    -u $(BECOME_USER) \
    -v $$(pwd):/src \
    -v $$(pwd)/.local:/.local \
    -v $(LOCAL_HOME)/.cache:/.cache \
    -v $(LOCAL_HOME)/.ccache:/.ccache \
    -e PIP_CACHE_DIR=/.cache \
    -v $(PROCESSING):/processing \
    -v $$(pwd)/run-tests/data:/projects \
    -v $$(pwd)/run-tests/__workdir__:/srv/data \
    -e QYWPS_LOGLEVEL=DEBUG \
    -e QYWPS_SERVER_PARALLELPROCESSES=$(WORKERS) \
    -e QYWPS_SERVER_LOGSTORAGE=$(LOGSTORAGE) \
    -e QYWPS_REDIS_HOST=$(REDIS_HOST) \
    -e QYWPS_PROCESSSING_PROVIDERS=$(PROVIDERS) \
    -e QYWPS_PROCESSSING_PROVIDERS_MODULE_PATH=/processing \
    -e QYWPS_CACHE_ROOTDIR=/projects \
    -e QYWPS_SERVER_WORKDIR=/srv/data \
    $(QGIS_IMAGE) /src/run-tests/setup.sh

client-test:
	rm -rf run-test/__workdir__/*
	py.test -v run-tests/tests/client/


