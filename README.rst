etcd for Twisted
================

`etcd3 <https://coreos.com/etcd/docs/latest/>`_ is a powerful building block in networked and distributed applications, which `Twisted <http://twistedmatrix.com/>`_ is an advanced substrate to implement in turn.

Hence the desire for a fully asynchronous etcd3 Twisted client with broad feature support: **txaioetcd**.

txaioetcd currently supports these etcd3 basic

- set and get values by key
- arbitrary byte strings for keys and values
- get values by range or prefix
- delete value (by single key, range and prefix)

and advanced features

- watch key sets with asynchronous callback
- create, refresh and delete leases
- submit transactions

txaioetcd also provides abstractions on top of the etcd3 transaction primitive:

- global locks and sequences
- transactional, multi-consumer-producer queues


Requirements
-------------

**etcd version 3.1 or higher** is required. etcd 2 will not work. etcd 3.0 also isn't enough - at least watching keys doesn't work over the gRPC HTTP gateway yet.

The implementation is pure Python code compatible with both **Python 2 and 3**, and runs perfect on **PyPy**.

The library requires **Twisted** (asyncio support could be added with no API break), but other than that only has minimal, Python-only dependencies.


Installation
------------

To install txaioetcd, use `pip <https://pip.pypa.io/en/stable/>`_ and

    pip install txaioetcd


Usage
-----

Here is an example etcd3 client that retrieves the cluster status

.. sourcecode:: python

    from twisted.internet.task import react
    from twisted.internet.defer import inlineCallbacks
    import txaioetcd
    import txaio

    @inlineCallbacks
    def main(reactor):
        client = txaioetcd.Client(reactor, u'http://localhost:2379')

        status = yield client.status()
        print(status)

        # insert one of the snippets below HERE

    if __name__ == '__main__':
        txaio.start_logging(level='info')
        react(main)

The following snippets demonstrate the etcd3 features supported by txaioetcd. To run the snippets, use the boilerplate above.


Getting values
..............

**Get a value by key** from etcd

.. sourcecode:: python

    try:
        value = yield client.get(b'/foo')
    except IndexError:
        print('no such key')
    else:
        print('value={}'.format(value))

or providing a default value

.. sourcecode:: python

    value = yield client.get(b'/foo', None)
    print('value={}'.format(value))

**Iterate** over key **range**

.. sourcecode:: python

    pairs = yield client.get(txaioetcd.KeySet(b'/foo1', b'/foo5'))
    for key, value in pairs.items():
        print('key={}: {}'.format(key, value))

**Iterate** over keys with given **prefix**

.. sourcecode:: python

    pairs = yield client.get(txaioetcd.KeySet(b'/foo', prefix=True))
    for key, value in pairs.items():
        print('key={}: {}'.format(key, value))


Setting values
..............

**Set** a value for some keys

.. sourcecode:: python

    for i in range(10):
        client.set('/foo{}'.format(i).encode(), b'woa;)')


Deleting keys
.............

**Delete** a (single) key

.. sourcecode:: python

    client.delete(b'/foo3')

**Delete** set of keys in given range

.. sourcecode:: python

    client.delete(txaioetcd.KeySet(b'/foo3', b'/foo7'))

**Delete** set of keys with given prefix and return previous key-value pairs

.. sourcecode:: python

    deleted = yield client.delete(txaioetcd.KeySet(b'/foo3'), return_previous=True)
    print('deleted key-value pairs: {}'.format(deleted))


Watching on keys
................

**Watch** keys for changes

.. sourcecode:: python

    # callback invoked for every change
    def on_change(key, value):
        print('watch callback fired for key {}: {}'.format(key, value))

    # start watching on set of keys with given prefix
    d = client.watch([txaioetcd.KeySet(b'/foo', prefix=True)], on_change)
    print('watching ..')

    # stop after 10 seconds
    yield sleep(10)
    d.cancel()


Design Goals
------------

We want etcd3 support because of the extended, useful functionality and semantics offered.

Supporting etcd2 using a restricted parallel API or by hiding away the differences between etcd2 and etcd3 seems ugly and we didn't needed etcd2 support anyway. So etcd2 support is a non-goal.

The implementation must be fully non-blocking and asynchronous, and must run on Twisted in particular. Supporting asyncio, or even a Python 3.5+ syntax for Twisted etc etc seems possible to add later without affecting the API.

The implementation must run fast on PyPy, which rules out using native code wrapped using cpyext. We also want to avoid native code in general, as it introduces security and memory-leak worries, and PyPy's JIT produces very fast code anyway.


Implementation
--------------

The library uses the `gRPC HTTP gateway <https://coreos.com/etcd/docs/latest/dev-guide/api_grpc_gateway.html>`_ within etcd3 and talks regular HTTP/1.1 with efficient long-polling for watching keys.

`Twisted Web agent <https://twistedmatrix.com/documents/current/web/howto/client.html>`_ and `treq <https://github.com/twisted/treq>`_ is used for HTTP, and both use a configurable Twisted Web HTTP connection pool.


Current limitations
-------------------

Missing asyncio support
.......................

The API of txaioetcd was designed not leaking anything from Twisted other than Deferreds. This is in line with the approach that txaio takes. It will allow us to add an asyncio implementation under the hood without affecting existing application code, but make the library run over either Twisted or asyncio, similar to txaio.

Missing native protocol support
...............................

The implementation talks HTTP/1.1 to the gRPC HTTP gateway of etcd3, and the binary payload is transmitted JSON with string values that Base64 encode the binary values of the etcd3 API.

Likely more effienct would be talk the native protocol of etcd3, which is HTTP/2 and gRPC/protobuf based. The former requires a HTTP/2 Twisted client. The latter requires a pure Python implementation of protobuf messages used and gRPC. So this is definitely some work, and probably premature optimization.

Missing dynamic watches
.......................

The HTTP/2 etcd3 native protocol allows to change a created watch on the fly. Maybe the gRPC HTTP gateway also allows that.

But I couldn't get a streaming *request* working with neither Twisted Web agent nor treq. A streaming *response* works of course, as in fact this is how the watch feature in txaioetcd is implemented.

And further, the API of txaioetcd doesn't expose it either. A watch is created, started and a Twisted Deferred (or possibly asyncio Future) is returned. The watch can be stopped by canceling the Deferred (Future) previously returned - but that is it. A watch cannot be changed after the fact.

Regarding the public API of txaioetcd, I think there will be a way that would allow adding dynamic watches that is upward compatible and hence wouldn't break any app code. So it also can be done later.

