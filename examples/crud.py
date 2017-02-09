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

from twisted.internet.task import react
from twisted.internet.defer import inlineCallbacks
from txaioetcd import Client, KeySet
import txaio


@inlineCallbacks
def main(reactor):
    etcd = Client(reactor, u'http://localhost:2379')

    # set values on keys
    for i in range(10):
        etcd.set('mykey{}'.format(i).encode(), b'hello')

    # get by key
    value = yield etcd.get(b'mykey1')
    print('value={}'.format(value))

    # get by key, providing default value if not found
    value = yield etcd.get(b'xyz', None)
    print('value={}'.format(value))

    # get by key and catch index error
    try:
        value = yield etcd.get(b'xyz')
    except IndexError:
        print('no such key')
    else:
        print('value={}'.format(value))

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
