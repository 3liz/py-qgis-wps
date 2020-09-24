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

# Minimal check with pylint because pylint choke on dynamic
# variables and members
# Disabled: 
#  * no-member (E1101)
#  * no-name-in-module (E0611)
#
PYTHONPATH=/usr/share/qgis/python/plugins/ \
    pylint -E -d E1101,E0611 /src/pyqgiswps

cd tests/unittests && pytest -v $@

