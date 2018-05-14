##################################################################
# Copyright 2016 OSGeo Foundation,                               #
# represented by PyWPS Project Steering Committee,               #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import sys
from imp import load_source


project = u'PyWPS'

license = ('This work is licensed under a Creative Commons Attribution 4.0 '
           'International License')

copyright = ('Copyright (C) 2014-2016 PyWPS Development Team, '
             'represented by Jachym Cepicky.')
copyright += license

version = load_source("version", '../qywps/version.py').__version__

release = version
latex_logo = '_static/qywps.png'

extensions = ['sphinx.ext.extlinks',
              'sphinx.ext.autodoc',
              'sphinx.ext.todo',
              'sphinx.ext.mathjax',
              'sphinx.ext.viewcode'
            ]
exclude_patterns = ['_build']
source_suffix = '.rst'
master_doc = 'index'

pygments_style = 'sphinx'

html_static_path = ['_static']

htmlhelp_basename = 'PyWPSdoc'
#html_logo = 'qywps.png'

html_theme = 'alabaster'
# alabaster settings
html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'searchbox.html',
    ]
}
html_theme_options = {
    'show_related': True,
    'travis_button': True,
    'github_banner': True,
    'github_user': 'geopython',
    'github_repo': 'qywps',
    'github_button': True,
    'logo': 'qywps.png',
    'logo_name': False
}

class Mock(object):
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return Mock()

    @classmethod
    def __getattr__(cls, name):
        if name in ('__file__', '__path__'):
            return '/dev/null'
        elif name[0] == name[0].upper():
            return Mock
        else:
            return Mock()

MOCK_MODULES = ['lxml', 'lxml.etree', 'lxml.builder']

#with open('../requirements.txt') as f:
#    MOCK_MODULES = f.read().splitlines()

for mod_name in MOCK_MODULES:
    sys.modules[mod_name] = Mock()

todo_include_todos = True
