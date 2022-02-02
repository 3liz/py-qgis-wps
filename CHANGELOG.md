# Changes

## Unreleased

## 1.6.7 - 2021-02-01

* Release the package on https://pypi.org/

## 1.6.6 - 2021-02-01

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
