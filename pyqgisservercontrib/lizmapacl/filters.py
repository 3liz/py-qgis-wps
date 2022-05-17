""" Handle lizmap WPS access policy 

autoreload: yes

# Define access policies
policies:
    # Global policy
    - deny: all

    # Policy for groups admin and operator
    - allow:  'scripts:*'
      groups: 
        - admin
        - operator

    # Policy for group operator will apply  only for map 'france_parts' with
    # testsimplevalue processes
    - allow: 'pyqgiswps_test:testsimplevalue'
      groups: 
        - operator
      maps:  
        - 'france_parts'

# Include other policies
include_policies:
    - lizmap_policies/*/wpspolicy.yml

"""
import sys
import logging
import yaml
import traceback

from itertools import chain

from typing import TypeVar, List, Dict, Generator
from pathlib import Path
from collections import namedtuple

from pyqgisservercontrib.core.watchfiles import watchfiles
from pyqgisservercontrib.core.filters import policy_filter

LOGGER = logging.getLogger('SRVLOG')

# Define an abstract types
YAMLData = TypeVar('YAMLData')

# Define an abstract type for HTTPRequest
HTTPRequest = TypeVar('HTTPRequest')


class LizmapPolicyError(Exception):
    pass

PolicyRule = namedtuple("PolicyRule", ('allow','deny','groups','users','maps'))

def _to_list(arg):
    """ Convert an argument to list
    """
    if isinstance(arg,list):
        return arg
    elif isinstance(arg,str):
        return arg.split(',')
    else:
        raise LizmapPolicyError("Expecting 'list' not %s" % type(arg))


def new_PolicyRule( allow=None, deny=None, groups=[], users=[], maps=[] ):
    """ Construct a PolicyRule object
    """
    return PolicyRule(allow  = allow,
                      deny   = deny,
                      groups = _to_list(groups),
                      users  = _to_list(users),
                      maps   = _to_list(maps))

# Define the 'all' group
GROUP_ALL='g__all'

class PolicyManager:
    
    @classmethod
    def initialize( cls, configfile: Path, exit_on_error: bool=True ) -> 'PolicyManager':
        """ Create policy manager
        """
        try:
            return PolicyManager(configfile)
        except Exception:
            LOGGER.error("Failed to initialize lizmap policy %s", configfile )
            if exit_on_error:
                traceback.print_exc()
                sys.exit(1)
            else:
                raise

    def __init__(self, configfile: Path ) -> None:
        self._autoreload = None
        self.load(configfile)

    def parse_policy( self, rootd: Path, config: YAMLData ) -> None:
        """
        """
        # Load rule from main config policies
        policies = [new_PolicyRule(**kw) for kw in config.get('policies',[])]

        # Load included policies
        for incl in config.get('include_policies',[]):
            for path in rootd.glob(incl):
                LOGGER.info("Policy: Opening policy rules: %s", path.as_posix())
                with path.open('r') as f:
                    acs = yaml.safe_load(f)
                # Add policies
                policies.extend( new_PolicyRule(**kw) for kw in acs )

        rules = { GROUP_ALL: [] }

        ### Create users/groups rule chain
        for ac in policies:
            if not ac.users and not ac.groups:
                rules[GROUP_ALL].append(ac)
                continue
            # Add user chain
            for k in chain( ('u__'+user for user in ac.users), ('g__'+group for group in ac.groups) ):
                r = rules.get(k,[])
                r.append(ac)
                rules[k] = r
 
        # Set policy rules
        self._rules = rules
        LOGGER.debug("# Lizmap Policy RULES %s", rules)

    def load( self, configfile: Path) -> None:
        """ Load policy configuration
        """
        LOGGER.info("Policy: Reading Lizmap Policy configuration %s", configfile)
        with configfile.open() as f:
            config = yaml.safe_load(f)
        
        self.parse_policy(configfile.parent, config)

        # Configure auto reload
        if config.get('autoreload', False):
            if self._autoreload is None:
                check_time = config.get('autoreload_check_time', 3000)
                self._autoreload = watchfiles([configfile.as_posix()], 
                                              lambda modified_files: self.load(configfile), 
                                              check_time=check_time)
            if not self._autoreload.is_running():
                LOGGER.info("Policy: Enabling Lizmap Policy autoreload")
                self._autoreload.start()
        elif self._autoreload is not None and self._autoreload.is_running():
            LOGGER.info("Policy: Disabling Lizmap Policy autoreload")
            self._autoreload.stop()            

    def add_policy_for(self, name:str, request: HTTPRequest) -> Generator:
        """ Add policy for the given name
        """
        rules = self._rules.get(name)
        if not rules:
            return
        for rule in rules:
            maps = rule.maps
            # Rule apply only for map
            if maps:
                test = request.arguments.get('MAP')
                # No map defined forget that rule
                if not test: 
                    continue
                test = test[-1]
                if isinstance(test,bytes):
                    test = test.decode()
                test = Path(test)
                # Test rule against map
                if not any( test.match(m) for m in maps ):
                    continue
            # Add policy
            yield dict(deny=rule.deny, allow=rule.allow)

    def add_policy(self, request: HTTPRequest) -> List[Dict]:
        """ Check profile condition
        """
        policies = []

        user    = request.headers.get('X-Lizmap-User')
        groups  = request.headers.get('X-Lizmap-User-Groups')
        if user:  
            policies.extend(self.add_policy_for('u__'+user, request))
        if groups:
            for group in groups.split(','):
                policies.extend(self.add_policy_for('g__'+group.strip(), request))
        # Add global rules
        policies.extend(self.add_policy_for(GROUP_ALL, request))

        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("# Lizmap policy USER: %s", user)
            LOGGER.debug("# Lizmap policy GROUPS: %s", groups)
            LOGGER.debug("# Lizmap policy ALLOW %s", [p['allow'] for p in policies])
            LOGGER.debug("# Lizmap policy DENY  %s", [p['deny'] for p in policies])

        return policies


def get_policies(policyfile: Path):
    mngr = PolicyManager.initialize(policyfile)

    @policy_filter()
    def _filter(request: HTTPRequest) -> List[Dict]:
        return mngr.add_policy(request)

    return [_filter]


def register_policy(policy_service, *args, **kwargs) -> None:
    """ Register filters
    """
    from  pyqgisservercontrib.core import componentmanager

    configservice = componentmanager.get_service('@3liz.org/config-service;1')
    configservice.add_section('extensions:lizmapacl')

    with_policy = configservice.get('extensions:lizmapacl','policy', fallback=None)
    if with_policy:
        policyfile = Path(with_policy)
        if not policyfile.exists():
            LOGGER.error("Lizmap Policy file is defined but does not exists: %s", policyfile)
            return
    
        policy_service.add_filters(get_policies(policyfile))


