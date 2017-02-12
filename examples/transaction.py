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
from txaioetcd import Client, KeySet, Transaction, \
    CompValue, CompVersion, CompCreated, CompModified, \
    OpGet, OpSet, OpDel, Failed


@inlineCallbacks
def main(reactor):

    etcd = Client(reactor, u'http://localhost:2379')

    #
    # Example 1
    #
    for val in [b'val1', b'val2']:

        yield etcd.set(b'test1', val)

        txn = Transaction(
            compare=[
                # compute conjunction of all terms to
                # determine "success" vs "failure"
                CompValue(b'test1', '==', b'val1')
            ],
            success=[
                # if true ("success"), run these ops
                OpSet(b'test1', b'val2'),
                OpSet(b'test2', b'success')
            ],
            failure=[
                # if not true ("failure"), run these ops
                OpSet(b'test2', b'failure'),
                OpGet(b'test1')
            ]
        )

        try:
            result = yield etcd.submit(txn)
        except Failed as failed:
            print('transaction FAILED:')
            for response in failed.responses:
                print(response)
        else:
            print('transaction SUCCESS:')
            for response in result.responses:
                print(response)

        for key in [b'test1', b'test2']:
            value = yield etcd.get(key)
            print('{}: {}'.format(key, value))

    #
    # Example 2
    #
    rev = yield etcd.set(b'mykey1', os.urandom(8))
    print(rev)

    result = yield etcd.get(b'mykey1')
    kv = result.kvs[0]
    print(kv)

    for version in [kv.version, kv.version - 1]:
        txn = Transaction(
            compare=[
                # value equality comparison
                CompValue(b'mykey1', '==', kv.value),

                # version, and different comparison operators
                CompVersion(b'mykey1', '==', version),
                CompVersion(b'mykey1', '!=', version + 1),
                CompVersion(b'mykey1', '<', version + 1),
                CompVersion(b'mykey1', '>', version - 1),

                # created revision comparison
                CompCreated(b'mykey1', '==', kv.create_revision),

                # modified revision comparison
                CompModified(b'mykey1', '==', kv.mod_revision),
            ],
            success=[
                OpSet(b'mykey2', b'success'),
                OpSet(b'mykey3', os.urandom(8))
            ],
            failure=[
                OpSet(b'mykey2', b'failure'),
                OpSet(b'mykey3', os.urandom(8))
            ]
        )

        try:
            result = yield etcd.submit(txn)
        except Failed as failed:
            print('transaction FAILED:')
            for response in failed.responses:
                print(response)
        else:
            print('transaction SUCCESS:')
            for response in result.responses:
                print(response)

        result = yield etcd.get(KeySet(b'mykey2', b'mykey4'))
        for kv in result.kvs:
            print(kv)


if __name__ == '__main__':
    txaio.start_logging(level='info')
    react(main)
