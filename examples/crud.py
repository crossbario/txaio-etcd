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

from twisted.internet.task import react
from twisted.internet.defer import inlineCallbacks

import txaio
from txaioetcd import Client, KeySet


@inlineCallbacks
def main(reactor):
    etcd = Client(reactor, u'http://localhost:2379')

    # set key-value, return revision including previous value
    revision = yield etcd.set(b'foo', os.urandom(8), return_previous=True)
    print(revision)

    # set values on keys
    for i in range(10):
        yield etcd.set('mykey{}'.format(i).encode(), os.urandom(8))

    # get value by key
    kv = yield etcd.get(b'mykey1')
    print('kv: {}'.format(kv))

    # get value by key, providing default value if not found
    kv = yield etcd.get(b'xyz', None)
    print('kv={}'.format(kv))

    # get by key and catch index error
    try:
        for key in [b'mykey0', b'xyz']:
            value = yield etcd.get(key)
    except IndexError:
        print('no such key: {}'.format(key))
    else:
        print(value)

    # iterate over keys in range
    kvs = yield etcd.get(KeySet(b'mykey1', b'mykey5'))
    for kv in kvs:
        print(kv)

    # iterate over keys with given prefix
    kvs = yield etcd.get(KeySet(b'mykey', prefix=True))
    for kv in kvs:
        print(kv)

    # delete a single key
    yield etcd.delete(b'mykey0')

    # delete a key range
    deleted = yield etcd.delete(KeySet(b'mykey2', b'mykey7'))
    print('deleted {} key-value pairs'.format(deleted.deleted))

    # delete a key set defined by prefix and return deleted key-value pairs
    deleted = yield etcd.delete(KeySet(b'mykey', prefix=True), return_previous=True)
    print(deleted)


if __name__ == '__main__':
    txaio.start_logging(level='info')
    react(main)
