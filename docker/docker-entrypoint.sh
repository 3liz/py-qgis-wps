#!/bin/bash
set -e

if [[ "$1" == "version" ]]; then
    version=`pip3 list | grep qgis-wps | tr -s [:blank:] | cut -d ' ' -f 2`
    qgis_version=`python3 -c "from qgis.core import Qgis; print(Qgis.QGIS_VERSION.split('-')[0])"`
    # Strip the 'rc' from the version
    # An 'rc' version is not released so as a docker image the rc is not relevant 
    # here
    echo "$qgis_version-${version%rc0}"
    exit 0
fi

#-------------------------------------------------------
# Set compatibility with legacy variable naming scheme
#-------------------------------------------------------
echo "Checking for legacy environment"
OLDVARS=`echo ${!QYWPS_*}`
for var in $OLDVARS; do
  varname=QGSWPS_`echo ${var#"QYWPS_"}`
  value=`echo ${!var}`
  echo "$varname=$value"
  export $varname=$value
done
#-------------------------------------------------------

QGSWPS_USER=${QGSWPS_USER:-"9001:9001"}

# Qgis need a HOME
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

# Run as QGSWPS_USER
exec wpsserver $@ -p 8080

