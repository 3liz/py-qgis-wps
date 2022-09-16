.. _access_control:

Job access control
==================

Access control to job list may be enforced by using realm token associated to jobs.  

When a job is created a token (a `realm`) may be associated to with it: this token
will be required used in subsequent requests  for 
accessing job's status and results or executing `dismiss` opération.

This feature is optional and is activated with the :ref:`SERVER_ENABLE_JOB_REALM`
configuration option.


Using realm token
------------------

By default, when a job is created, a realm token is created and associated to the job. 

This token is either defined implicitely by creating a unique uuid and returning the value
in the `X-Job-Realm` header of the execution response or set explicitely using the same header
in the request.

This token may then be inspected by the client and used in subsequent requests  for 
accessing job's status and results or executing `dismiss` opération. 

Typical usage is to have a middleware proxy that sets the `X-Job-Realm` header together with specifie authentification procedure. 


Administrative realm
---------------------

When enabling realm, a administrator may be defined. Requesting job's control using such a token will bypass
any other tokens and will give full access to job's list.

This admin token is defined with the :ref:`SERVER_ADMIN_REALM` configuration option.








