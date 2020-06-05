##################################################################
# Copyright 2017 3liz                                            #
# licensed under MIT, Please consult LICENSE.txt for details     #
##################################################################

from setuptools import setup, find_namespace_packages


def parse_requirements( filename ):
    with open( filename ) as fp:
        return list(filter(None, (r.strip('\n ').partition('#')[0] for r in fp.readlines())))

kwargs = {}

VERSION = "1.4.1"
DESCRIPTION = ('Py-Qgis-WPS is an implementation of the Web Processing Service '
               'standard from the Open Geospatial Consortium. qgis-wps is '
               'written in Python and is a fork of PyWPS 4.0.')
KEYWORDS = 'QGIS WPS OGC processing'
INSTALL_REQUIRES = parse_requirements('requirements.txt')

setup(
    name='py-qgis-wps',
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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: GIS'
    ],
    install_requires=INSTALL_REQUIRES,
    packages=find_namespace_packages(include=['pyqgiswps','pyqgiswps.*',
                                              'pyqgisservercontrib.*']),
    include_package_data = True,
    entry_points={
        'console_scripts': ['wpsserver = pyqgiswps.wpsserver:main'],
    },

    **kwargs
)

