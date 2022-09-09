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
$PIP_INSTALL -q --prefer-binary -r requirements.pip
$PIP_INSTALL -q --prefer-binary -r requirements.txt

$PIP install -e ./ 

export QGIS_DISABLE_MESSAGE_HOOKS=1
export QGIS_NO_OVERRIDE_IMPORT=1

# Do no resart workers on each run
export QGSWPS_SERVER_PROCESSLIFECYCLE=0

# see https://docs.python.org/3/library/faulthandler.html
export PYTHONFAULTHANDLER=1

cd tests/unittests && exec $VENV_PATH/bin/pytest -v $@

