SHELL:=bash
# 
# Build docker image
#
#

NAME=qgis-wps

BUILDID=$(shell date +"%Y%m%d%H%M")
COMMITID=$(shell git rev-parse --short HEAD)

FLAVOR:=release

# Server version
BUILD_VERSION:=$(shell cd .. && python3 setup.py --version)
ifeq ($(BUILD_VERSION),)
$(error failed to retrieve build version)
endif

ifdef PYPISERVER
PYPISERVER_SCHEME ?= https
PIP_OPTIONS="--extra-index-url=$(PYPISERVER_SCHEME)://$(PYPISERVER) --trusted-host=$(PYPISERVER) --pre"
DOCKERFILE=-f Dockerfile.pypi
BUILD_ARGS=--build-arg PIP_OPTIONS=$(PIP_OPTIONS)
else
BUILD_PACKAGE=build_package
endif

BUILD_ARGS += --build-arg BUILD_VERSION=$(BUILD_VERSION)
BUILD_ARGS += --build-arg QGIS_VERSION=$(FLAVOR)

REGISTRY_URL ?= 3liz
REGISTRY_PREFIX=$(REGISTRY_URL)/
BUILD_ARGS += --build-arg REGISTRY_PREFIX=$(REGISTRY_PREFIX)

export BUILDIMAGE:=$(NAME):$(FLAVOR)-$(COMMITID)

MANIFEST=factory.manifest

all:
	@echo "Usage: make [build|deliver|clean]"

build: _build manifest

_build: $(BUILD_PACKAGE)
	docker build --rm --force-rm --no-cache $(DOCKER_BUILD_ARGS) \
		$(BUILD_ARGS) -t $(BUILDIMAGE) $(DOCKERFILE) .

build_package:
	rm -rf dist && mkdir -p dist
	$(MAKE) -C .. dist DIST=$$PWD/dist

manifest:
	{ \
	set -e; \
	version=`docker run --rm $(BUILDIMAGE) version`; \
	version_short=`echo $$version | cut -d- -f1 |cut -d. -f1-2`-`echo $$version | cut -d- -f2 |cut -d. -f1-2`; \
	echo name=$(NAME) > $(MANIFEST) && \
    echo version=$$version >> $(MANIFEST) && \
    echo version_short=$$version_short >> $(MANIFEST) && \
    echo release_tag=`echo $$version | cut -d- -f1 |cut -d. -f1-2` >> $(MANIFEST) && \
    echo buildid=$(BUILDID)   >> $(MANIFEST) && \
    echo commitid=$(COMMITID) >> $(MANIFEST); }

deliver: tag push

tag:
	{ set -e; source factory.manifest; \
	docker tag $(BUILDIMAGE) $(REGISTRY_PREFIX)$(NAME):$$version; \
	docker tag $(BUILDIMAGE) $(REGISTRY_PREFIX)$(NAME):$$version_short; \
	docker tag $(BUILDIMAGE) $(REGISTRY_PREFIX)$(NAME):$$release_tag; \
	docker tag $(BUILDIMAGE) $(REGISTRY_PREFIX)$(NAME):$(FLAVOR); \
	}

push:
	{ set -e; source factory.manifest; \
	docker push $(REGISTRY_URL)/$(NAME):$$version; \
	docker push $(REGISTRY_URL)/$(NAME):$$version_short; \
	docker push $(REGISTRY_URL)/$(NAME):$$release_tag; \
	docker push $(REGISTRY_URL)/$(NAME):$(FLAVOR); \
	}


clean-all:
	docker rmi -f $(shell docker images $(BUILDIMAGE) -q)

clean:
	docker rmi $(BUILDIMAGE)

export BECOME_USER=$(shell id -u):$(shell id -g)
export SRCDIR:=$(shell realpath ..)
export RUNDIR:=$(SRCDIR)/tests/unittests

env:
	@@{\
		echo "Creating environment file for docker-compose";\
		echo "BECOME_USER=${BECOME_USER}" > .env;\
		echo "SRCDIR=${SRCDIR}" >> .env;\
		echo "RUNDIR=${RUNDIR}" >> .env;\
	}


run: stop env
	@echo "NOTE: Pour redémarrer un service, considérez plutôt:"
	@echo "  > docker-compose restart <service>"
	docker-compose up

stop:
	docker-compose stop  || true
	docker-compose rm -f || true

# Client tests, run the service first
test:
	py.test -v tests/


