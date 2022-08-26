##################################################################
# Copyright 2017 3liz                                            #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

import os
from setuptools import setup, find_namespace_packages


def parse_requirements( filename ):
    with open( filename ) as fp:
        return list(filter(None, (r.strip('\n ').partition('#')[0] for r in fp.readlines())))

def get_version():
    with open('VERSION') as fp:
        return fp.read().strip()

kwargs = {}
VERSION = get_version()
DESCRIPTION = ('Py-Qgis-WPS is an implementation of the Web Processing Service '
               'standard from the Open Geospatial Consortium. qgis-wps is '
               'written in Python and is a fork of PyWPS 4.0.')
KEYWORDS = 'QGIS WPS OGC processing'
INSTALL_REQUIRES = parse_requirements('requirements.txt')

with open('README.md') as f:
    content_readme = f.read()


builtin_access_policies = [
    'lizmap_acl = pyqgisservercontrib.lizmapacl.filters:register_policy',
]


setup(
    name='py-qgis-wps',
    version=VERSION,
    description=DESCRIPTION,
    keywords=KEYWORDS,
    author='David Marteau',
    author_email='david.marteau@3liz.com',
    maintainer='David Marteau',
    maintainer_email='david.marteau@3liz.com',
    long_description=content_readme,
    long_description_content_type="text/markdown",
    url='https://github.com/3liz/py-qgis-wps',
    python_requires=">=3.6",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: GIS'
    ],
    install_requires=INSTALL_REQUIRES,
    packages=find_namespace_packages(include=['pyqgiswps','pyqgiswps.*',
                                              'pyqgisservercontrib.*']),
    include_package_data = True,
    entry_points={
        'console_scripts': [
            'wpsserver = pyqgiswps.wpsserver:main',
            'wpsserver-check = pyqgiswps.healthcheck:main'
        ],
        'py_qgis_wps.access_policy': [
            'lizmap_acl = pyqgisservercontrib.lizmapacl.filters:register_policy',
        ],
    },

    **kwargs
)

