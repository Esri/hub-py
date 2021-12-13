from setuptools import setup, find_packages, find_namespace_packages

# from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))
REQUIRES_PYTHON = '>=3.7.0'
setup(
    name='arcgishub',
    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='3.0.0',
    description='ArcGIS Hub Python API',
    long_description='Python API to automate your Hub processes',
    requires_python=REQUIRES_PYTHON,
    # Author details
    author='Esri',
    # Choose your license
    license='Proprietary License',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4',
        # Indicate who your project is intended for
        'Intended Audience :: Developers, Hub Customers',
        # Pick your license as you wish (should match "license" above)
        'License :: Other/Proprietary License',
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    # What does your project relate to?
    keywords='gis geographic spatial hub arcgis initiatives',
    packages=find_namespace_packages(
        include=['arcgis.*'],
    ),
    include_package_data=True,
    # package_data={'arcgis.apps.hub._store': ['init-sites-data.json']},
    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['six', 'arcgis>=2.0.0'],
)
