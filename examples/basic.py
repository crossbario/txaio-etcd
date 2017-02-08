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

from autobahn.twisted.util import sleep

from txaioetcd import Client
import txaio


@inlineCallbacks
def main(reactor):

    # a Twisted etcd client
    client = Client(reactor, u'http://localhost:2379')

    # get etcd status
    status = yield client.status()
    print(status)

    # get value for a key
    try:
        value = yield client.get(b'/cf/foo')
        print('value={}'.format(value))
    except IndexError:
        print('no such key =(')

    # set a value for some keys
    for i in range(3):
        rev = yield client.set('/cf/foo0{}'.format(i).encode(), b'woa;)')
        print('value set, revision={}'.format(rev))

    # delete key
    key = u'/cf/foo02'.encode()
    deleted = yield client.delete(key)
    print(deleted)

    # iterate over key range (maybe an async iter in the future?)
    pairs = yield client.get(b'/cf/foo01', b'/cf/foo05')
    for key, value in pairs.items():
        print('key={}: {}'.format(key, value))

    # iterate over keys with given prefix
    pairs = yield client.get(b'/cf/foo0', prefix=True)
    for key, value in pairs.items():
        print('key={}: {}'.format(key, value))

    # watch keys for change events
    prefixes = [b'/cf/', b'/foo/']

    # our callback that will be invoked for every change event
    def on_watch(key, value):
        print('watch callback fired for key {}: {}'.format(key, value))

    # start watching on given key prefixes
    d = client.watch(prefixes, on_watch)

    # sleep for n seconds ..
    delay = 10
    print('watching {} for {} seconds ..'.format(prefixes, delay))
    yield sleep(delay)

    # .. and stop watching
    yield d.cancel()

    # submit transaction

    # create lease

if __name__ == '__main__':
    txaio.start_logging(level='info')
    react(main)
