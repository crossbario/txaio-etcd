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

import txaio
from txaioetcd import Client, KeySet, Transaction, \
    CompValue, CompVersion, OpGet, OpSet, OpDel, Failed


@inlineCallbacks
def main(reactor):
    # create an etcd client
    etcd = Client(reactor, u'http://localhost:2379')

    # retrieve etcd cluster status
    status = yield etcd.status()
    print(status)

    yield etcd.set(b'goo', b'bar')

    txn = Transaction(
        compare=[
            CompValue(b'goo', '==', b'bar'),
            CompVersion(b'goo', '==', 23)
        ],
        success=[
            OpSet(b'poo', b'baz'),
            OpSet(b'test', b'done'),
            OpDel(KeySet(b'foo', prefix=True))
        ],
        failure=[
            OpSet(b'goo', b'bar'),
            OpSet(b'goo2', b'bar'),
            OpDel(KeySet(b'foo', prefix=True)),
        ]
    )

    try:
        result = yield etcd.submit(txn)
    except Failed as failed:
        print('transaction FAILED with these responses:')
        for response in failed.responses:
            print(response)
    else:
        print('transaction SUCCESS with these responses:')
        for response in result.responses:
            print(response)


if __name__ == '__main__':
    txaio.start_logging(level='info')
    react(main)
