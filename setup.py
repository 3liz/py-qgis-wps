##################################################################
# Copyright 2017 3liz                                            #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

from setuptools import setup, find_packages, Extension


def parse_requirements( filename ):
    with open( filename ) as fp:
        return list(filter(None, (r.strip('\n ').partition('#')[0] for r in fp.readlines())))


def load_source(name, path):
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location(name, path)
    mod  = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

kwargs = {}

VERSION = load_source("version", 'qywps/version.py').__version__
DESCRIPTION = ('Qgis-wps is an implementation of the Web Processing Service '
               'standard from the Open Geospatial Consortium. qgis-wps is '
               'written in Python and is a fork of PyWPS 4.0.')
KEYWORDS = 'QGIS WPS OGC processing'
INSTALL_REQUIRES = parse_requirements('requirements.txt')

setup(
    name='qgis-wps',
    version=VERSION,
    description=DESCRIPTION,
    keywords=KEYWORDS,
    author='David Marteau',
    author_email='david.marteau@3liz.com',
    maintainer='David Marteau',
    maintainer_email='david.marteau@3liz.com',
    url='https://github.com/3liz/py-qgis-wps',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: GIS'
    ],
    install_requires=INSTALL_REQUIRES,
    packages=find_packages(include=['qywps','qywps.*']),
    include_package_data = True,
    entry_points={
        'console_scripts': ['wpsserver = qywps.wpsserver:main'],
    },

    **kwargs
)

