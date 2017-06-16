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
from txaioetcd import Client, KeySet


@inlineCallbacks
def main(reactor):
    # create an etcd client
    etcd = Client(reactor, u'http://localhost:2379')

    # retrieve etcd cluster status
    status = yield etcd.status()
    print(status)

    # callback invoked for every change
    def on_change(kv):
        print('on_change: {}'.format(kv))

    # start watching on given keys or key sets
    # when the key sets overlap, the callback might get called multiple
    # times, once for each key set matching an event
    keys = [KeySet(b'mykey2', b'mykey5'), KeySet(b'mykey', prefix=True)]
    d = etcd.watch(keys, on_change)

    # stop after 10 seconds
    print('watching for 10s ..')
    yield txaio.sleep(10)
    d.cancel()


if __name__ == '__main__':
    txaio.start_logging(level='info')
    react(main)
