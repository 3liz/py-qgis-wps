#!/bin/bash
set -e

copy_qgis_configuration() {
    QGIS_CUSTOM_CONFIG_PATH=${QGIS_CUSTOM_CONFIG_PATH:-$QGIS_OPTIONS_PATH}
    if [[ -n $QGIS_CUSTOM_CONFIG_PATH ]]; then
        echo "Copying Qgis configuration: $QGIS_CUSTOM_CONFIG_PATH"
        mkdir -p $HOME/profiles/default
        cp -RL $QGIS_CUSTOM_CONFIG_PATH/* $HOME/profiles/default
    fi
    export QGIS_CUSTOM_CONFIG_PATH=$HOME
    export QGIS_OPTIONS_PATH=$HOME
}


if [[ "$1" == "version" ]]; then
    version=`/opt/local/pyqgiswps/bin/pip list | grep qgis-wps | tr -s [:blank:] | cut -d ' ' -f 2`
    qgis_version=`python3 -c "from qgis.core import Qgis; print(Qgis.QGIS_VERSION.split('-')[0])"`
    # Strip the 'rc' from the version
    # An 'rc' version is not released so as a docker image the rc is not relevant
    # here
    echo "$qgis_version-${version%rc0}"
    exit 0
fi


QGSWPS_USER=${QGSWPS_USER:-"9001:9001"}

# QGIS need a HOME
export HOME=/home/qgis

if [ "$(id -u)" = '0' ]; then
   mkdir -p $HOME
   chown -R $QGSWPS_USER $HOME
   # Change ownership of $QGSWPS_SERVER_WORKDIR
   # This is necessary if it is mounted from a named volume
   chown -R $QGSWPS_USER $QGSWPS_SERVER_WORKDIR

   # Run as QGSWPS_USER
   exec gosu $QGSWPS_USER  "$BASH_SOURCE" $@
fi

copy_qgis_configuration

# Run as QGSWPS_USER
exec wpsserver $@ -p 8080
