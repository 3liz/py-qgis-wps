
ifdef REGISTRY_URL
REGISTRY_PREFIX=$(REGISTRY_URL)/
endif

LOCAL_PORT:=127.0.0.1:8080

LOGSTORAGE:=REDIS
REDIS_HOST:=redis
PROVIDERS:=lzmtest
PROCESSING:=$(shell pwd)
WORKERS:=2

BECOME_USER:=$(shell id -u)

run:
	docker run -it --rm -p $(LOCAL_PORT):8080 \
    -v $(PROCESSING):/processing \
    -v $(shell pwd)/data:/projects \
    -v $(shell pwd)/__workdir__:/srv/data \
    -e QYWPS_SERVER_LOGSTORAGE=$(LOGSTORAGE) \
    -e QYWPS_SERVER_PARALLELPROCESSES=$(WORKERS) \
    -e QYWPS_REDIS_HOST=$(REDIS_HOST) \
    -e QYWPS_PROCESSSING_PROVIDERS=lzmtest \
    -e QYWPS_PROCESSSING_PROVIDERS_MODULE_PATH=/processing \
    -e QYWPS_CACHE_ROOTDIR=/projects \
    -e QYWPS_SERVER_WORKDIR=/srv/data \
    -e QYWPS_USER=$(BECOME_USER):$(BECOME_USER) \
    qgis3-wps-service

