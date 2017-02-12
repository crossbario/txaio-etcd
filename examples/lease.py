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
from txaioetcd import Client, Expired


@inlineCallbacks
def main(reactor):

    etcd = Client(reactor, u'http://localhost:2379')

    status = yield etcd.status()
    print(status)

    yield example1(reactor, etcd)
    yield example2(reactor, etcd)
    yield example3(reactor, etcd)
    yield example4(reactor, etcd)
    yield example5(reactor, etcd)


@inlineCallbacks
def example1(reactor, etcd):

    print("\n\nEXAMPLE 1")

    print('creating lease with 5s TTL')
    lease = yield etcd.lease(5)
    print(lease)

    i = 1
    while True:
        try:
            remaining = yield lease.remaining()
            i += 1
        except Expired:
            if i == 5:
                print('lease expired (expected)')
                break
            else:
                raise
        else:
            print('lease TTL = {}'.format(remaining))
            print('sleeping for 1s ..')
            yield txaio.sleep(1)


@inlineCallbacks
def example2(reactor, etcd):

    print("\n\nEXAMPLE 2")

    print('creating lease with 5s TTL')
    lease = yield etcd.lease(5)
    print(lease)

    print('refreshing lease every 4s, 5 times ..')
    for i in range(5):
        rev = yield lease.refresh()
        print(rev)
        yield txaio.sleep(4)

    print('sleeping for 6s ..')
    yield txaio.sleep(6)

    print('refreshing lease')
    try:
        yield lease.refresh()
    except Expired:
        print('leave expired (expected)')


@inlineCallbacks
def example3(reactor, etcd):

    print("\n\nEXAMPLE 3")

    print('creating lease with 5s TTL')
    lease = yield etcd.lease(5)
    print(lease)

    print('sleeping for 2s ..')
    yield txaio.sleep(2)

    print('revoking lease')
    res = yield lease.revoke()
    print(res)
    print('refreshing lease')

    try:
        yield lease.refresh()
    except Expired:
        print('leave expired (expected)')


@inlineCallbacks
def example4(reactor, etcd):

    print("\n\nEXAMPLE 4")

    print('creating lease with 5s TTL')
    lease = yield etcd.lease(5)
    print(lease)

    yield etcd.set(b'foo', b'bar', lease=lease)

    i = 0
    while True:
        result = yield etcd.get(b'foo')
        if result.kvs:
            kv = result.kvs[0]
            print(kv)
            i += 1
        else:
            print('key has been deleted together with expired lease ({}s)'.format(i))
            break

        print('sleeping for 1s ..')
        yield txaio.sleep(1)


@inlineCallbacks
def example5(reactor, etcd):

    print("\n\nEXAMPLE 5")

    print('creating lease with 5s TTL')
    lease = yield etcd.lease(5)
    print(lease)

    keys = yield lease.keys()
    print(keys)

    yield etcd.set(b'foo', b'bar', lease=lease)

    keys = yield lease.keys()
    print(keys)

    yield etcd.delete(b'foo')

    keys = yield lease.keys()
    print(keys)


if __name__ == '__main__':
    txaio.start_logging(level='info')
    react(main)
