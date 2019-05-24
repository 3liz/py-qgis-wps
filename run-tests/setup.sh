#!/bin/bash

set -e

# Add /.local to path
export PATH=$PATH:/.local/bin

echo "Installing python package, please wait...."

pip3 install -q -U --user setuptools
pip3 install -q -U --user -r requirements.pip
pip3 install -q --user -r requirements.txt 
pip3 install --user -e ./ 

export QGIS_DISABLE_MESSAGE_HOOKS=1
export QGIS_NO_OVERRIDE_IMPORT=1

exec wpsserver -w $WORKERS -p 8080 --chdir run-tests

