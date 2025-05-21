# Changes


## Unreleased


### 1.10.0 - 2025-05-21

* Deprecate `WPSClassFactory` in favor of `initProcessing`
* Fix deprecation warnings

## 1.9.2 - 2024-12-16

* release update

## 1.9.1 - 2024-12-16

* Enforce python 3.10 requirement
* Do not use deprecated datetime.utcnow
    - From https://github.com/3liz/py-qgis-wps/pull/65

## 1.9.0 - 2024-11-13

* Remove support for Qgis < 3.28
* Remove dependency on 3liz/qgis-platform images for tests
* Remove deprecated store apis:
    - `/store/`
    - `/ows/store/` 
* Remove postgres cache handler in favor of generic Qgis storage

## 1.8.7 - 2024-07-15

* Disable broken strict complex geojson validation
* geometryio: Allow to use a crs in a geojson feature
    - From https://github.com/3liz/py-qgis-wps/pull/47

## 1.8.6 - 2023-04-13

* Merge pull request #38 from ptitjano/xml-element-warning
* Add advertised WCS/WFS urls in output QGIS project
    - Fix https://github.com/3liz/py-qgis-wps/issues/28
* Fix Sample config (https://github.com/3liz/py-qgis-wps/issues/32)
* Fix QGIS 3.30 supports
* Merge pull request #37 from ptitjano/wip/jfelder/complexinput-supportedformats

## 1.8.5 - 2023-03-28

* Use quote format for layers parameter name in output urls
    - Fix urlencoded parameters with space: 
      i.e: `layers=foo%20bar` instead of `layers=foo+bar` that
      causes problem with QGIS server.

## 1.8.4 - 2022-12-16

* PEP8 Code style
* Fix schemas in OGC API/processes description.
* Fix: load layer default styles with `loadDefaultStyle`

## 1.8.3 - 2022-12-08

* Fix invalid decoding of complex data as base64
    - Fix https://github.com/3liz/py-qgis-wps/issues/31
* Fix mandatory SERVICE parameters for POST WPS requests
* Deprecate `host_proxy` in favor of `proxy_url` option
* Define explicit `HTTP\_PROXY` option
    - Handling of proxyfied urls may be disabled
* Check access control (realm) for direct resource download
* Support overriding service url for OWS requests 
    - Follow QGIS server convention for passing service url
* Fix rel link to XML results from job description
    - Links to WPS GetResults request
    - `jobs/<id>/results` now return 404 for OWS/WPS results
    - fix https://github.com/3liz/py-qgis-wps/issues/30

## 1.8.2 - 2022-09-28

* Fix packaging of html elements 
    - Was preventing alternate html link to work
      (fix https://github.com/3liz/py-qgis-wps/issues/29)

## 1.8.1 - 2022-09-27

* Fix errors when handlings 'band' parameters
    - Was preventing publishing `gdal` internal provider 
* Replace calls to asyncio.get\_event\_loop()

## 1.8.0 - 2022-09-19

* Add OpenAPI description
* Landing page as root location
* Optional server infos page (disabled by default)
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
* Skip capabilities check for QGIS >= 3.26.1

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
