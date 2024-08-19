SHELL:=bash
.ONESHELL:
.PHONY: env

DEPTH=..

include $(DEPTH)/config.mk

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

SRCDIR=$(topsrcdir)

TESTS_CPU_LIMITS:=2.0
TESTS_MEMORY_LIMITS:=2g
WORKERS:=1

env:
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

# see https://docs.python.org/3/library/faulthandler.html
test: export PYTHONFAULTHANDLER=1
test:
	SRCDIR=$(SRCDIR) source tests.env \
	&& export $$(cut -d= -f1 tests.env) \
	&& cd unittests \
	&& pytest -v $(PYTEST_ADDOPTS)

#test: export RUN_COMMAND=/src/tests/run-tests.sh
#test: up

run: export RUN_COMMAND=/src/tests/run-server.sh
run: up

stop: 
	docker compose down -v --remove-orphans

up: env
	docker compose up -V --quiet-pull --remove-orphans \
		--force-recreate --exit-code-from wps
	docker compose down -v --remove-orphans

