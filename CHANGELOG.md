# Changes

## Unreleased

* Deprecate apis in favor of ogc api:
    - Deprecate `/status/` in favor of `/jobs/<uuid>/status/`
    - Deprecate `/store/` in favor of `/jobs/<uuid>/files`
    - Deprecate `/ui/` in favor of `/jobs.html`
    Deprecated apis will be removed in 1.9
* Implement Job realm support
* Support for ogc processes open api
* Improve UOM validation
* Use of UCUM references for UOM
    - See https://ucum.org/
* Code cleaning
* Support options `DISABLE_GETPRINT` and `TRUST_LAYER_METADATA`
* Skip capabilities check for Qgis >= 3.26.1

## 1.7.0 - 2022-05-17

* Refactorize access policy managment
* Add restart notification on provider changes
* Remove fakeredis dependency
* Use docker compose for tests

## 1.6.7 - 2022-02-01

* Release the package on https://pypi.org/

## 1.6.6 - 2022-02-01

* Install server in venv in docker image
* Add support for inputs:
    * 'Mesh' layer parameter
    * QgsProcessingParameterDistance
    * QgsProcessingParameterDuration
    * QgsProcessingParameterScale
* Fix BoundingBox input
    * Fix crs from bounding box input
    * Allow bounding box as kvp input data
* Refactorize OWS requests
    * Allow support for multiple formats
* Clean dead code 
* Use PyTest `log-cli-*` options for enabling logger output"  

## 1.6.5 - 2021-09-21

* Handle providers exception
* Add tests for geometry parameter

## 1.6.4 - 2021-07-21

* Add SSL options
* Improve documentation

## 1.6.3 - 2021-06-08

* Support 'allowMultipart' metadata for geometry inputs
    * See https://github.com/qgis/QGIS/pull/42403
* Set CRS to destination projects:
    * Validate source project CRS
    * Define default CRS
* Implement live reload of providers plugins

## 1.6.2 - 2021-05-20

* Unsafe option for saving results at absolute location 
* Add CORS support
* Code cleaning
