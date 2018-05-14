.. _configuration:

Configuration
=============

PyWPS is configured using a configuration file. The file uses the
`ConfigParser <https://wiki.python.org/moin/ConfigParserExamples>`_ format.

.. versionadded:: 4.0.0
.. warning:: Compatibility with PyWPS 3.x: major changes have been made
  to the config file in order to allow for shared configurations with `PyCSW
  <http://pycsw.org/>`_ and other projects.

The configuration file has 3 sections:

    * `metadata:main` for the server metadata inputs
    * `server` for server configuration
    * `loggging` for logging configuration
    * `grass` for *optional* configuration to support `GRASS GIS
      <http://grass.osgeo.org>`_

PyWPS ships with a sample configuration file (``default-sample.cfg``). 
A similar file is also available in the `demo` service as
described in :ref:`demo` section.

Copy the file to ``default.cfg`` and edit the following: 

[metadata:main]
---------------

The `[metadata:main]` section was designed according to the `PyCSW project
configuration file <http://docs.pycsw.org/en/latest/configuration.html>`_.

:identification_title:
    the title of the service
:identification_abstract:
    some descriptive text about the service
:identification_keywords:
    comma delimited list of keywords about the service
:identification_keywords_type:
    keyword type as per the `ISO 19115 MD_KeywordTypeCode codelist
    <http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#MD_KeywordTypeCode>`_).
    Accepted values are ``discipline``, ``temporal``, ``place``, ``theme``,
    ``stratum``
:identification_fees:
    fees associated with the service
:identification_accessconstraints:
    access constraints associated with the service
:provider_name:
    the name of the service provider
:provider_url:
    the URL of the service provider
:contact_name:
    the name of the provider contact
:contact_position:
    the position title of the provider contact
:contact_address:
    the address of the provider contact
:contact_city:
    the city of the provider contact
:contact_stateorprovince:
    the province or territory of the provider contact
:contact_postalcode:
    the postal code of the provider contact
:contact_country:
    the country of the provider contact
:contact_phone:
    the phone number of the provider contact
:contact_fax:
    the facsimile number of the provider contact
:contact_email:
    the email address of the provider contact
:contact_url:
    the URL to more information about the provider contact
:contact_hours:
    the hours of service to contact the provider
:contact_instructions:
    the how to contact the provider contact
:contact_role:
    the role of the provider contact as per the `ISO 19115 CI_RoleCode codelist
    <http://www.isotc211.org/2005/resources/Codelist/gmxCodelists.xml#CI_RoleCode>`_).
    Accepted values are ``author``, ``processor``, ``publisher``, ``custodian``,
    ``pointOfContact``, ``distributor``, ``user``, ``resourceProvider``,
    ``originator``, ``owner``, ``principalInvestigator``

[server]
--------

:url:
    the URL of the WPS service endpoint

:language:
    the ISO 639-1 language and ISO 3166-1 alpha2 country code of the service
    (e.g. ``en-CA``, ``fr-CA``, ``en-US``)

:encoding:
    the content type encoding (e.g. ``ISO-8859-1``, see
    https://docs.python.org/2/library/codecs.html#standard-encodings).  Default
    value is 'UTF-8'

:parallelprocesses:
    maximum number of parallel running processes - set this number carefully.
    The effective number of parallel running processes is limited by the number 
    of cores  in the processor of the hosting machine. As well, speed and 
    response time of hard drives impact ultimate processing performance. A 
    reasonable number of parallel running processes is not higher than the 
    number of processor cores.

:maxrequestsize:
    maximal request size. 0 for no limit 
    
:workdir: 
    a directory to store all temporary files (which should be always deleted, 
    once the process is finished).
    
:outputpath: 
    server path where to store output files.

:outputurl:
    corresponding URL

.. note:: `outputpath` and `outputurl` must corespond. `outputpath` is the name
        of the resulting target directory, where all output data files are
        stored (with unique names). `outputurl` is the corresponding full URL, 
        which is targeting to `outputpath` directory.

        Example: `outputpath=/var/www/wps/outputs` shall correspond with
        `outputurl=http://foo.bar/wps/outputs`

[logging]
---------

:level:
    the logging level (see
    http://docs.python.org/library/logging.html#logging-levels)

:file:
    the full file path to the log file for being able to see possible error
    messages.

:database:
    Connection string to database where the login about requests/responses is to be stored. We are using `SQLAlchemy <http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls>`_
    please use the configuration string. The default is SQLite3 `:memory:` object.


[grass]
-------

:gisbase:
  directory of the GRASS GIS instalation, refered as `GISBASE
  <https://grass.osgeo.org/grass73/manuals/variables.html>`_

-----------
Sample file
-----------
::

  [server]
  encoding=utf-8
  language=en-US
  url=http://localhost/wps
  maxoperations=30
  maxinputparamlength=1024
  maxsingleinputsize=
  maxrequestsize=3mb
  temp_path=/tmp/qywps/
  outputurl=/data/
  outputpath=/tmp/outputs/
  logfile=
  loglevel=INFO
  logdatabase=
  workdir=
  
  [metadata:main]
  identification_title=PyWPS Processing Service
  identification_abstract=PyWPS is an implementation of the Web Processing Service standard from the Open Geospatial Consortium. PyWPS is written in Python.
  identification_keywords=PyWPS,WPS,OGC,processing
  identification_keywords_type=theme
  identification_fees=NONE
  identification_accessconstraints=NONE
  provider_name=Organization Name
  provider_url=http://qywps.org/
  contact_name=Lastname, Firstname
  contact_position=Position Title
  contact_address=Mailing Address
  contact_city=City
  contact_stateorprovince=Administrative Area
  contact_postalcode=Zip or Postal Code
  contact_country=Country
  contact_phone=+xx-xxx-xxx-xxxx
  contact_fax=+xx-xxx-xxx-xxxx
  contact_email=Email Address
  contact_url=Contact URL
  contact_hours=Hours of Service
  contact_instructions=During hours of service.  Off on weekends.
  contact_role=pointOfContact

  [grass]
  gisbase=/usr/local/grass-7.3.svn/
