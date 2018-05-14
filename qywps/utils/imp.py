""" Import utilities 
"""

__all__ = ['load_source']


from importlib.util import spec_from_file_location, module_from_spec

def load_source(name, path):
    """ Mimic the deprecated  'imp.load_source' function
    """
    spec = spec_from_file_location(name, path)
    mod  = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

