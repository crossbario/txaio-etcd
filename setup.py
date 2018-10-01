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

import os
from setuptools import setup, find_packages


# read package version
with open('txaioetcd/_version.py') as f:
    exec(f.read())  # defines __version__

# read package description
with open('README.rst') as f:
    docstr = f.read()

# we read requirements from requirements*.txt files down below
install_requires = []
extras_require = {
    'dev': []
}

# minimum, open-ended requirements
reqs = 'requirements.txt'

with open(reqs) as f:
    for line in f.read().splitlines():
        line = line.strip()
        if not line.startswith('#'):
            parts = line.strip().split(';')
            if len(parts) > 1:
                parts[0] = parts[0].strip()
                parts[1] = ':{}'.format(parts[1].strip())
                if parts[1] not in extras_require:
                    extras_require[parts[1]] = []
                extras_require[parts[1]].append(parts[0])
            else:
                install_requires.append(parts)

with open('requirements-dev.txt') as f:
    for line in f.read().splitlines():
        extras_require['dev'].append(line.strip())


setup(
    name='txaioetcd',
    version=__version__,
    description='Asynchronous client library for etcd3',
    long_description=docstr,
    license='MIT License',
    author='Crossbar.io Technologies GmbH',
    author_email='autobahnws@googlegroups.com',
    url='https://github.com/crossbario/txaio-etcd',
    platforms=('Any', ),
    install_requires=install_requires,
    extras_require=extras_require,
    packages=find_packages(),

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
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries",
    ],
    keywords='twisted etcd etcd3',

    entry_points={
        'console_scripts': [
            'etcd-export = txaioetcd.cli.exporter:main',
            'etcd-import = txaioetcd.cli.importer:main'
        ]
    },
)
