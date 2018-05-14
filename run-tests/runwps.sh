#!/usr/bin/env bash

set -x
set -e

# Run docker image from 3liz repository
# Ne pas oublier de  lancer un redis aver la commande
# docker run -it --rm -p 6379:6379 --name redis --net mynet redis:4


LOCAL_PORT=${LOCAL_PORT:-127.0.0.1:8080}
WORKERS=${WORKERS:-2}

DOCKER_IMAGE=${DOCKER_IMAGE:-3liz/qgis3-wps-service}
USERID=$(id -u)

LOGSTORAGE=REDIS

mkdir -p __workdir__
docker run -it --rm -p $LOCAL_PORT:8080 --name qgis3-wps-test --net mynet \
    -v $(pwd):/processing \
    -v $(pwd)/data:/projects \
    -v $(pwd)/__workdir__:/srv/data \
    -e QYWPS_SERVER_PARALLELPROCESSES=$WORKERS \
    -e QYWPS_SERVER_LOGSTORAGE=$LOGSTORAGE \
    -e QYWPS_REDIS_HOST=redis \
    -e QYWPS_PROCESSSING_PROVIDERS=lzmtest \
    -e QYWPS_PROCESSSING_PROVIDERS_MODULE_PATH=/processing \
    -e QYWPS_CACHE_ROOTDIR=/projects \
    -e QYWPS_SERVER_WORKDIR=/srv/data \
    -e QYWPS_USER=$USERID:$USERID \
    $DOCKER_IMAGE


