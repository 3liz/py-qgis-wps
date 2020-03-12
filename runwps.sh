#!/bin/bash

set -e

mkdir -p __outputdata___
export QGSWPS_SERVER_PARALLELPROCESSES=1
export QGSWPS_CACHE_ROOTDIR=$PWD/tests/unittests/data
export QGSWPS_PROCESSING_PROVIDERS_MODULE_PATH=$PWD/tests/unittests
export QGSWPS_SERVER_WORKDIR=$PWD/__outputdata___
export QGIS_OPTIONS_PATH=$PWD/tests/qgis
export QGSWPS_LOGLEVEL=DEBUG
export QGSWPS_REDIS_HOST=localhost


wpsserver -p 8080

