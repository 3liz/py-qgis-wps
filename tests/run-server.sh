#!/bin/bash

set -e

# Add /.local to path
export PATH=$PATH:/.local/bin

echo "-- HOME is $HOME"

echo "Installing python package, please wait...."

pip3 install -U -q --user setuptools
pip3 install --no-warn-script-location -q --user --prefer-binary -r requirements.txt 
pip3 install --user -e ./ 

export QGIS_DISABLE_MESSAGE_HOOKS=1
export QGIS_NO_OVERRIDE_IMPORT=1

export FAKEREDIS=yes

exec wpsserver -w $WORKERS -p 8080 --chdir tests/unittests

