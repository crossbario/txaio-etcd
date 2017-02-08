###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Crossbar.io Technologies GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

from setuptools import setup


with open('txaioetcd/_version.py') as f:
    exec(f.read())  # defines __version__

with open('README.rst') as f:
    docstr = f.read()

extras_require_dev = [
    'pytest>=2.6.4',                    # MIT
    'pytest-cov>=1.8.1',                # MIT
    'pep8>=1.6.2',                      # MIT
    'sphinx>=1.2.3',                    # BSD
    'pyenchant>=1.6.6',                 # LGPL
    'sphinxcontrib-spelling>=2.1.2',    # BSD
    'sphinx_rtd_theme>=0.1.9',          # BSD
    'tox>=2.1.1',                       # MIT
    'mock==1.3.0',                      # BSD
    'twine>=1.6.5',                     # Apache 2.0
]

setup(
    name='txaioetcd',
    version=__version__,
    description='A Twisted client for etcd3',
    long_description=docstr,
    author='Crossbar.io Technologies GmbH',
    url='https://github.com/crossbario/txaio-etcd',
    platforms=('Any'),
    install_requires=[
        'six',                          # MIT
        'zope.interface>=3.6',          # Zope Public License
        'twisted>=12.1.0',              # MIT
        'txaio',                        # MIT
    ],
    extras_require={
        'dev': extras_require_dev,
    },
    packages=['txaioetcd'],
    zip_safe=True,
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Framework :: Twisted",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries",
    ],
    keywords='twisted etcd etcd3',
)
