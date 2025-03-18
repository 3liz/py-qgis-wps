SHELL:=bash
# 
# Build docker image
#
#

DEPTH=..

include $(DEPTH)/config.mk

NAME=qgis-wps

FLAVOR:=release

# Server version
BUILD_VERSION:=$(VERSION_TAG)

ifdef PYPISERVER
PYPISERVER_SCHEME ?= https
PIP_OPTIONS="--extra-index-url=$(PYPISERVER_SCHEME)://$(PYPISERVER) --trusted-host=$(PYPISERVER)"
BUILD_ARGS=--build-arg PIP_OPTIONS=$(PIP_OPTIONS)
endif

BUILD_ARGS += --build-arg BUILD_VERSION=$(BUILD_VERSION)
BUILD_ARGS += --build-arg QGIS_VERSION=$(FLAVOR)

REGISTRY_URL ?= 3liz
REGISTRY_PREFIX=$(REGISTRY_URL)/
BUILD_ARGS += --build-arg REGISTRY_PREFIX=$(REGISTRY_PREFIX)

BUILDIMAGE:=$(NAME):$(FLAVOR)-$(COMMITID)

MANIFEST=factory-$(FLAVOR).manifest

# Use buildkit 
export DOCKER_BUILDKIT=1

all:
	@echo "Usage: make [build|deliver|clean]"

#DOCKER_CACHE:=--force-rm --no-cache

build: manifest
	docker build --rm $(DOCKER_CACHE) $(DOCKER_BUILD_ARGS) \
		$(BUILD_ARGS) -t $(BUILDIMAGE) -f Dockerfile ..

QGIS_IMAGE=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)

manifest:
	{ \
	set -e; \
	version=`docker run --rm -v $$(pwd)/scripts:/scripts $(QGIS_IMAGE)  /scripts/qgis-version.sh`; \
	echo name=$(NAME) > $(MANIFEST) && \
    echo version=$$version-$(VERSION) >> $(MANIFEST) && \
    echo version_short=$$version >> $(MANIFEST) && \
    echo release_tag=`echo $$version | cut -d- -f1 |cut -d. -f1-2` >> $(MANIFEST) && \
    echo buildid=$(BUILDID)   >> $(MANIFEST) && \
    echo commitid=$(COMMITID) >> $(MANIFEST); }

deliver: tag push

ifndef CI_COMMIT_TAG

GIT_BRANCH=$(shell git branch --show-current)
ifeq ($(GIT_BRANCH),)
GIT_BRANCH=$(CI_COMMIT_BRANCH)
endif

ifeq ($(GIT_BRANCH),master)
TAG_DEV=dev
else
TAG_DEV=$(GIT_BRANCH)-dev
endif

tag:
	{ set -e; source $(MANIFEST); \
	docker tag $(BUILDIMAGE) $(REGISTRY_PREFIX)$(NAME):$${release_tag}-$(TAG_DEV); \
	docker tag $(BUILDIMAGE) $(REGISTRY_PREFIX)$(NAME):$(FLAVOR)-$(TAG_DEV); \
	}

push:
	{ set -e; source $(MANIFEST); \
	docker push $(REGISTRY_URL)/$(NAME):$${release_tag}-$(TAG_DEV); \
	docker push $(REGISTRY_URL)/$(NAME):$(FLAVOR)-$(TAG_DEV); \
	}

else

tag:
	{ set -e; source $(MANIFEST); \
	docker tag $(BUILDIMAGE) $(REGISTRY_PREFIX)$(NAME):$$version; \
	docker tag $(BUILDIMAGE) $(REGISTRY_PREFIX)$(NAME):$$version_short; \
	docker tag $(BUILDIMAGE) $(REGISTRY_PREFIX)$(NAME):$$release_tag; \
	docker tag $(BUILDIMAGE) $(REGISTRY_PREFIX)$(NAME):$(FLAVOR); \
	}

push:
	{ set -e; source $(MANIFEST); \
	docker push $(REGISTRY_URL)/$(NAME):$$version; \
	docker push $(REGISTRY_URL)/$(NAME):$$version_short; \
	docker push $(REGISTRY_URL)/$(NAME):$$release_tag; \
	docker push $(REGISTRY_URL)/$(NAME):$(FLAVOR); \
	}

endif

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
	@echo "  > docker compose restart <service>"
	BUILDIMAGE=$(BUILDIMAGE) docker compose up

stop:
	BUILDIMAGE=$(BUILDIMAGE) docker compose down -v

# Client tests, run the service first
test:
	py.test -v tests/

# Push to docker hub as rc version
pushrc:
ifdef CI_COMMIT_TAG
	@echo "This is a TAG commit"
else
	@cat $(DOCKERPASS) | docker login -u 3liz --password-stdin
	docker tag $(BUILDIMAGE) 3liz/$(NAME):$(FLAVOR)-rc
	docker push 3liz/$(NAME):$(FLAVOR)-rc
endif

