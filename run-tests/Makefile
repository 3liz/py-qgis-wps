SHELL=bash
#
# Run server from source and client tests
#

ifdef REGISTRY_URL
REGISTRY_PREFIX=$(REGISTRY_URL)/
endif

FLAVOR:=ltr

export QGIS_IMAGE:=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)
export BECOME_USER:=$(shell id -u)
export SRCDIR:=$(shell realpath ..)
export WORKERS:=1
ifndef LOCAL_HOME
export LOCAL_HOME=$(shell pwd)
endif


local:
	rm -rf .local/share
	mkdir -p  .local  $(LOCAL_HOME)/.ccache $(LOCAL_HOME)/.cache

run: local stop
	mkdir -p __workdir__
	docker-compose up

test:
	rm -rf __workdir__/*
	pytest -v tests/client/

stop:
	docker-compose stop  || true
	docker-compose rm -f || true

