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

    rev = yield etcd.set(b'mykey1', os.urandom(8))
    print(rev)

    kv = yield etcd.get(b'mykey1')
    print(kv)

    for version in [kv.version, kv.version - 1]:
        txn = Transaction(
            compare=[
                CompValue(b'mykey1', '==', kv.value),
                CompVersion(b'mykey1', '==', version),
                CompCreated(b'mykey1', '==', kv.create_revision),
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

        kvs = yield etcd.get(KeySet(b'mykey2', b'mykey4'))
        for kv in kvs:
            print(kv)


if __name__ == '__main__':
    txaio.start_logging(level='info')
    react(main)
