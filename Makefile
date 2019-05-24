.PHONY: test
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


