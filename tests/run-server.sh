#!/bin/bash

set -e

echo "-- HOME is $HOME"

VENV_PATH=/.local/venv

PIP="$VENV_PATH/bin/pip"
PIP_INSTALL="$VENV_PATH/bin/pip install -U"

echo "-- Creating virtualenv"
python3 -m venv --system-site-packages $VENV_PATH

echo "-- Installing required packages..."
$PIP_INSTALL -q pip setuptools wheel
$PIP_INSTALL -q --prefer-binary -r requirements.txt

$PIP install -e .

export QGIS_DISABLE_MESSAGE_HOOKS=1
export QGIS_NO_OVERRIDE_IMPORT=1

export QGSWPS_SERVER_PARALLELPROCESSES=$WORKERS

cd tests/unittests
exec $VENV_PATH/bin/wpsserver -p 8080

