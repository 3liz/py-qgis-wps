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

QGIS_IMAGE:=$(REGISTRY_PREFIX)qgis-platform-dev:latest

# This is necessary with pytest as long it is not fixed
# see also https://github.com/qgis/QGIS/pull/5337
export QGIS_DISABLE_MESSAGE_HOOKS := 1
export QGIS_NO_OVERRIDE_IMPORT := 1

dirs:
	mkdir -p $(DIST)

manifest:
	echo name=$(shell $(PYTHON) setup.py --name) > $(MANIFEST) && \
    echo version=$(shell $(PYTHON) setup.py --version) >> $(MANIFEST) && \
    echo buildid=$(BUILDID)   >> $(MANIFEST) && \
    echo commitid=$(COMMITID) >> $(MANIFEST)

ptest:
	PYTHONPATH=$(shell pwd)/tests QYWPS_SERVER_LOGSTORAGE=DBLOG $(PYTHON) tests/pywps_tests/__init__.py

qtest:
	cd tests/qywps_tests && py.test -v

test: ptest qtest


# Define a pip conf to use
#
PIP_CONFIG_FILE:=pip.conf
BECOME_USER:=$(shell id -u)

ifndef LOCAL_HOME
LOCAL_HOME=$(shell pwd)
endif

docker-test:
	mkdir -p $(HOME)/.local $(shell pwd)/.ccache
	docker run --rm --name qgis3-wps-test-$(COMMITID) -w /src \
    -u $(BECOME_USER) \
    -v $(shell pwd):/src \
    -v $(LOCAL_HOME)/.local:/.local \
    -v $(LOCAL_HOME)/.cache/pip:/.pipcache \
    -v $(shell pwd)/.ccache:/.ccache \
    -e PIP_CACHE_DIR=/.pipcache \
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
# docker run -it --rm --name redis --net mynet redis:4

docker-run:
	@echo "Do not forget to run 'docker run -it --rm -p 6379:6379 --name redis --net mynet redis:4'"
	mkdir -p $(HOME)/.local
	mkdir -p $(shell pwd)/run-tests/__workdir__
	mkdir -p $(shell pwd)/run-tests/__ccache__
	docker run -it --rm -p $(LOCAL_PORT):8080 --name qgis3-wps-run-$(COMMITID) $(DOCKER_OPTIONS) -w /src \
    -u $(BECOME_USER) \
    -v $(shell pwd):/src \
    -v $(HOME)/.local:/.local \
    -v $(HOME)/.config/pip:/.pipconf  \
    -v $(HOME)/.cache/pip:/.pipcache \
    -v $(shell pwd)/run-tests/__ccache__:/.ccache \
    -e PIP_CONFIG_FILE=/.pipconf/$(PIP_CONFIG_FILE) \
    -e PIP_CACHE_DIR=/.pipcache \
    -v $(PROCESSING):/processing \
    -v $(shell pwd)/run-tests/data:/projects \
    -v $(shell pwd)/run-tests/__workdir__:/srv/data \
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


