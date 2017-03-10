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

from __future__ import absolute_import

from txaioetcd._version import __version__

from txaioetcd._types import KeySet, KeyValue, Header, Status, \
    Deleted, Revision, \
    Comp, CompValue, CompVersion, CompCreated, CompModified, \
    Op, OpGet, OpSet, OpDel, Transaction, Expired, Error, Failed, Success, \
    Range

from txaioetcd._lease import Lease

if True:
    from txaioetcd._client_tx import Client
else:
    from txaioetcd._client_aio import Client


# This is the complete public API of txaioetcd:
__all__ = (
    '__version__',

    'Client',
    'Transaction',
    'Lease',

    'KeyValue',
    'KeySet',
    'Header',
    'Status',
    'Range',
    'Revision',
    'Deleted',

    'Error',
    'Failed',
    'Success',
    'Expired',

    'Comp',
    'CompValue',
    'CompVersion',
    'CompCreated',
    'CompModified',

    'Op',
    'OpGet',
    'OpSet',
    'OpDel',

)

version = __version__
