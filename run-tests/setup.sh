#!/bin/bash

set -e

pip3 install -U --user setuptools
pip3 install -U --user -r requirements.pip
pip3 install -U --user -r requirements.txt 

pip3 install --user -e ./ 

export QGIS_DISABLE_MESSAGE_HOOKS=1
export QGIS_NO_OVERRIDE_IMPORT=1

# Add /.local to path
export PATH=$PATH:/.local/bin

exec wpsserver -w 1 -p 8080 --chdir run-tests

