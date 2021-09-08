#!/bin/bash

set -e

# Add /.local to path
export PATH=$PATH:/.local/bin

echo "-- HOME is $HOME"

pip3 install -U --user setuptools
pip3 install --no-warn-script-location --user --prefer-binary -r requirements.pip
pip3 install --no-warn-script-location --user --prefer-binary -r requirements.txt 

pip3 install --user -e ./ 

export QGIS_DISABLE_MESSAGE_HOOKS=1
export QGIS_NO_OVERRIDE_IMPORT=1

# Do no resart workers on each run
export QGSWPS_SERVER_PROCESSLIFECYCLE=0

export PYTHONFAULTHANDLER=1

cd tests/unittests && pytest -v $@

