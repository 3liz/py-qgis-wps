SHELL:=bash
.ONESHELL:
.PHONY: env
#
#  Makefile for running server in docker containers
#
COMMITID=$(shell git rev-parse --short HEAD)

REGISTRY_URL ?= 3liz
REGISTRY_PREFIX=$(REGISTRY_URL)/

FLAVOR:=release

QGIS_IMAGE:=$(REGISTRY_PREFIX)qgis-platform:$(FLAVOR)

# Define a pip conf to use
#
BECOME_USER:=$(shell id -u)

SERVER_HTTP_PORT:=127.0.0.1:8888

SRCDIR=$(shell realpath ..)

local:
	@rm -rf unittests/__outputdir__/*
	@mkdir -p $$(pwd)/__workdir__
	@mkdir -p  $$(pwd)/.local  $$(pwd)/.cache

clean:
	@rm -rf $$(pwd)/.local $$(pwd)/.cache

TESTS_CPU_LIMITS:=2.0
TESTS_MEMORY_LIMITS:=2g

WORKERS:=1

env: local
	@echo "Creating environment file for docker-compose"
	@cat <<-EOF > .env
		BECOME_USER=$(BECOME_USER)
		QGIS_IMAGE=$(QGIS_IMAGE)
		WORKERS=$(WORKERS)
		SRCDIR=$(SRCDIR)
		PYTEST_ADDOPTS="$(PYTEST_ADDOPTS)"
		CPU_LIMITS=$(TESTS_CPU_LIMITS)
		MEMORY_LIMITS=$(TESTS_MEMORY_LIMITS)
		COMPOSE_PROJECT_NAME=test-pyqgiswps
		EOF

test: export RUN_COMMAND=/src/tests/run-tests.sh
test: env up

run: export RUN_COMMAND=/src/tests/run-server.sh
run: up

stop:
	docker compose down -v --remove-orphans

up:
	docker compose up -V --quiet-pull --remove-orphans \
		--force-recreate --exit-code-from wps
	docker compose down -v --remove-orphans

test-pool: local
	docker run --rm --name qgis-wps-test-pool-$(FLAVOR)-$(COMMITID) -w /src \
    -u $(BECOME_USER) \
    -v $(SRCDIR):/src \
    -v $$(pwd)/.local:/.local \
    -v $$(pwd)/.cache:/.cache \
    -e PIP_CACHE_DIR=/.cache \
    -e PYTEST_ADDOPTS="$(PYTEST_ADDOPTS)" \
    $(QGIS_IMAGE) /src/tests/run-pool-tests.sh

