#!/bin/bash

set -e

# Add /.local to path
export PATH=$PATH:/.local/bin

echo "-- HOME is $HOME"

pip3 install -U --user setuptools
pip3 install --no-warn-script-location --user --prefer-binary -r requirements.txt
pip3 install --user -e ./ 

python3 -m pyqgiswps.poolserver

