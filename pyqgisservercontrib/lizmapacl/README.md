# Lizmap access policy filter plugin for py-qgis-wps

Middleware filter for managing access control policy for [py-qgis-wps](https://github.com/3liz/py-qgis-wps)

## Description

This extension allow to define access policy for WPS processe for Lizmap user and Lizmap groups

Access policies ared defined with two directives: 'deny' and 'allow'. 
Each entry define a  list of ar defined as comma separated list of processes identifiers. 
Globbing style wildcards are allowed.

Order of evaluation is allow/deny, if one directive match, the other is not evaluated. If none match
then full access is granted.

Example of access policy definition that allow only 'scripts' processing scripts for group operators:

```
   - deny: all
     allow: 'script:*'
     groups: operator
```

Forbidden processes will not show in `GetCapabilities` and `DescribeProcess` or `Execute` will return a 403 HTTP error.


Multiple rules can be configured, first all `allow` directives will be tested then all `deny` directive. 
That is, order is not significant when defining rules.


## Policy configuration

Policy rules are configured using a YAML file. The  path to this configuration file 
is given by the `QGSWPS_EXTENSIONS_LIZMAPACL_POLICY` environment variable or the  `policy` variable
in the `[extensions:lizmapacl]` section of the [py-qgis-wps](https://github.com/3liz/py-qgis-wps) configuration.

Example of policy configuration:

```
# Hot reload policy configuration when file change - no
# need to restart server 
autoreload: yes

# Define access policies
policies:
    # Global policy, forbid access to all processes to everybody
    - deny: all

    # Policy for groups admin and operator
    - allow:  'scripts:*'
      groups: 
        - admin
        - operator

    # Allow 'scripts:private' only for users 'franck' and 'helen'
    - allow: 'scripts:private'
      users: franck, helen

    # Policy rule for group operator that apply only for map 'france_parts'
    - allow: 'pyqgiswps_test:testsimplevalue'
      groups: 
        - operator
      maps:  
        - 'france_parts

    # Policy 'pyqgiswps_test:*' for everyone but only for map 'france_parts'
    - allow: 'pyqgiswps_test:*'
      maps: 'france_parts'


# Include other policies
include_policies:
    - lizmapacls/*/*.yml
```


## Policy directives

- `deny` : a list of processes forbidden, globing style wildcards are allowed.
- `allow`: a list of allowed processes, globing style wildcards are allowed.
- `users`: a list of users for which the rule apply
- `groups`: a list of groups for which the rule apply
- `maps`: a liste of MAPS parameter for which the rule apply, globing wildcards are allowed.



