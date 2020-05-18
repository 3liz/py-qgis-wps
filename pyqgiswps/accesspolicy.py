#
# Handle access policy for processes
#

import yaml
import logging

from pathlib import Path
from typing import List, Union
from itertools import chain

from pyqgiswps.config import confservice

LOGGER = logging.getLogger('SRVLOG')


class InvalidPolicyError(Exception):
    pass


def _validate_policy( rules: Union[str,List[str]] ) -> List[str]:
    if rules == 'all': 
        rules = ['*']
    elif isinstance(rules, str): 
        rules = [rules]
    elif not isinstance(rules, list) or not all( isinstance(r,str) for r in  rules):
        raise InvalidPolicyError()
    return rules



class AccessPolicy:

    def __init__(self):
       self._allow = []
       self._deny  = []

    def add_policy( self, deny: List[str]=None, allow: List[str]=None ) -> None:
        """ Add custom policy
        """
        if allow:
            self._allow.extend(_validate_policy(allow))
        if deny:
            self._deny.extend(_validate_policy(deny))

    def allow( self, identifier: str ) -> bool:
        """ Check policy for identifier
        """
        return default_access_policy.allow(identifier,self)


class DefaultPolicy:

    def __init__(self):
        self._deny  = []
        self._allow = []

    def init(self, filepath: Union[str,Path]=None) -> None:
        """ Load policy file
        """
        if not isinstance(filepath,Path):
            filepath = Path(filepath or confservice.get('processing','accesspolicy'))
        if not filepath.exists():
            return

        LOGGER.info("Loading access policy from %s", filepath.as_posix())

        with filepath.open('r') as f:
            policy = yaml.load(f, yaml.SafeLoader)

        self._deny  = _validate_policy(policy.get('deny' ,[]))
        self._allow = _validate_policy(policy.get('allow',[]))

    def allow( self, identifier: str, childpolicy: AccessPolicy ) -> bool:
        """ Check policy for identifier 
        """
        ident = Path(identifier)
        allowed = any( ident.match(d) for d in chain(self._allow, childpolicy._allow) )
        if allowed:
            return True
        return not any( ident.match(d) for d in chain(self._deny, childpolicy._deny) )
      

#
# Single DefaultPolicy instance
#
default_access_policy = DefaultPolicy()

def init_access_policy(filepath: Union[str,Path]=None) -> None:
    default_access_policy.init(filepath)

def new_access_policy() -> AccessPolicy:
    return AccessPolicy() 





