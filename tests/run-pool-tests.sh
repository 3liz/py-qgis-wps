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

$VENV_PATH/bin/python3 -m pyqgiswps.poolserver

