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

    # set key-value
    etcd.set(b'foo', os.urandom(8))

    # set key-value, return revision including previous value
    revision = yield etcd.set(b'foo', os.urandom(8), return_previous=True)
    print('previous:', revision.previous)

    # set values on keys
    for i in range(10):
        etcd.set('mykey{}'.format(i).encode(), os.urandom(8))

    # get value by key
    for key in [b'mykey1', KeySet(b'mykey1'), b'mykey13']:
        result = yield etcd.get(key)
        if result.kvs:
            kv = result.kvs[0]
            print(kv)
        else:
            print('key {} not found!'.format(key))

    # iterate over keys in range
    result = yield etcd.get(KeySet(b'mykey1', b'mykey5'))
    print('KV pairs for range:')
    for kv in result.kvs:
        print(kv)

    # iterate over keys with given prefix
    result = yield etcd.get(KeySet(b'mykey', prefix=True))
    print('KV pairs for prefix:')
    for kv in result.kvs:
        print(kv)

    # delete a single key
    deleted = yield etcd.delete(b'mykey0')
    print('deleted {} key-value pairs'.format(deleted.deleted))

    # delete non-existing key
    deleted = yield etcd.delete(os.urandom(8))
    print('deleted {} key-value pairs'.format(deleted.deleted))

    # delete a key range
    deleted = yield etcd.delete(KeySet(b'mykey2', b'mykey7'))
    print('deleted {} key-value pairs'.format(deleted.deleted))

    # delete a key set defined by prefix and return deleted key-value pairs
    deleted = yield etcd.delete(KeySet(b'mykey', prefix=True), return_previous=True)
    print('deleted {} key-value pairs:'.format(deleted.deleted))
    for d in deleted.previous:
        print(d)


if __name__ == '__main__':
    txaio.start_logging(level='info')
    react(main)
