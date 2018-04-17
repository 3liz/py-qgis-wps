##################################################################
# Copyright 2017 3liz                                            #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

from setuptools import setup, find_packages, Extension

def parse_requirements( filename ):
    import os
    if os.path.exists( filename ):
        with open( filename ) as fp:
            return list(filter(None, (r.strip('\n').partition('#')[0] for r in fp.readlines())))
    return []

def load_source(name, path):
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location(name, path)
    mod  = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

kwargs = {}

VERSION = load_source("version", 'qywps/version.py').__version__
DESCRIPTION = ('QYWPS is an implementation of the Web Processing Service '
               'standard from the Open Geospatial Consortium. QWPS is '
               'written in Python and is a fork of PyWPS 4.0.')
KEYWORDS = 'QYWPS WPS OGC processing'
INSTALL_REQUIRES = parse_requirements('requirements.txt')

setup(
    name='QYWPS',
    version=VERSION,
    description=DESCRIPTION,
    keywords=KEYWORDS,
    license='MIT',
    platforms='all',
    author='David Marteau',
    author_email='david.marteau@3liz.com',
    maintainer='David Marteau',
    maintainer_email='david.marteau@3liz.com',
    url='',
    download_url='',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
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
        'qywps.logstorage':[
            'DBLOG=qywps.executors.logstorage.dblog:DBStore',
            'REDIS=qywps.executors.logstorage.redislog:RedisStore'
        ],
        'console_scripts': ['wpsserver = qywps.wpsserver:main'],
    },

    **kwargs
)

