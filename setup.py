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
    'sphinx',
    'sphinx_rtd_theme',
    'twine',                            # Apache 2.0
]

setup(
    name='txaioetcd',
    version=__version__,
    description='Asynchronous client library for etcd3',
    long_description=docstr,
    license='MIT License',
    author='Crossbar.io Technologies GmbH',
    author_email='autobahnws@googlegroups.com',
    url='https://github.com/crossbario/txaio-etcd',
    platforms=('Any'),
    install_requires=[
        'six>=1.10.0',                  # MIT
        'twisted>=16.6.0',              # MIT
        'treq>=16.12.0',                # MIT
        'txaio>=2.6.1',                 # MIT
    ],
    extras_require={
        'dev': extras_require_dev,
    },
    packages=['txaioetcd'],

    # this flag will make files from MANIFEST.in go into _source_ distributions only
    include_package_data=True,

    # in addition, the following will make the specified files go
    # into source _and_ bdist distributions!
    data_files=[('.', ['LICENSE'])],

    # this package does not access its own source code or data files
    # as normal operating system files
    zip_safe=True,

    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 4 - Beta",
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries",
    ],
    keywords='twisted etcd etcd3',
)
