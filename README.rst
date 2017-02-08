txetcd3
=======

**txetcd3** is a Twisted client for `etcd3 <https://coreos.com/etcd/docs/latest/>`_ and supports the following features of etcd3:

- set/get value by key with arbitrary byte strings for both
- get values by range
- delete value (single key and by range)
- watch keys and key prefixes with asynchronous callback


Requirements
-------------

**etcd version 3.1 or higher** is required. etcd 2 will not work. etcd 3.0 also isn't enough - at least watching keys doesn't work over the gRPC HTTP gateway yet.

The implementation is pure Python code compatible with both **Python 2 and 3**, and runs perfect on **PyPy**.

The library (obviously) requires **Twisted**, but other than that only has minimal, Python-only dependencies.


Installation
------------

To install txetcd3, use `pip <https://pip.pypa.io/en/stable/>`_ and

    pip install txetcd3


Usage
-----

Boilerplate
...........

To create a client and get etcd status, run the following

.. sourcecode:: python

    from twisted.internet.task import react
    from twisted.internet.defer import inlineCallbacks
    import txetcd3
    import txaio

    @inlineCallbacks
    def main(reactor):
        # a Twisted etcd client
        client = txetcd3.Client(reactor, u'http://localhost:2379')

        # get etcd status
        status = yield client.status()
        print(status)

        # insert one of the snippets below HERE

    if __name__ == '__main__':
        txaio.start_logging(level='info')
        react(main)

Snippets
........

The following snippets demonstrate the etcd3 features supported by txetcd3. To run the snippets, use the boilerplate above.

To **get a value by key** from etcd

.. sourcecode:: python

    # get value for a key
    try:
        value = yield client.get(b'/cf/foo')
    except IndexError:
        print('no such key')
    else:
        print('value={}'.format(value))

**Set a value** for a bunch of keys

.. sourcecode:: python

    for i in range(10):
        yield client.set('/cf/foo{}'.format(i).encode(), b'woa;)')

**Delete** a (single) key

.. sourcecode:: python

    yield client.delete(b'/cf/foo3')

**Iterate** over key **range**

.. sourcecode:: python

    pairs = yield client.get(b'/cf/foo1', b'/cf/foo5')
    for key, value in pairs.items():
        print('key={}: {}'.format(key, value))

**Iterate** over keys with given **prefix**

.. sourcecode:: python

    pairs = yield client.get(b'/cf/foo', prefix=True)
    for key, value in pairs.items():
        print('key={}: {}'.format(key, value))

**Watch** keys for changes

.. sourcecode:: python

    # our callback that will be invoked for every change event
    def on_watch(key, value):
        print('watch callback fired for key {}: {}'.format(key, value))

    # start watching on given key prefixes
    d = client.watch([b'/cf/foo'], on_watch)

    # watch for 10 seconds and then stop watching
    print('watching ..')
    yield sleep(10)
    yield d.cancel()


Design Goals
------------

We want etcd3 support because of the extended, useful functionality and semantics offered.

Supporting etcd2 using a restricted parallel API or by hiding away the differences between etcd2 and etcd3 seems ugly and we didn't needed etcd2 support anyway. So etcd2 support is a non-goal.

The implementation must be fully non-blocking and asynchronous, and must run on Twisted in particular.

The implementation must run fast on PyPy, which rules out using native code wrapped using cpyext. We also want to avoid native code in general, as it introduces security and memory-leak worries, and PyPy's JIT produces very fast code anyway.


Implementation
--------------

The library uses the `gRPC HTTP gateway <https://coreos.com/etcd/docs/latest/dev-guide/api_grpc_gateway.html>`_ within etcd3 and talks regular HTTP/1.1 with efficient long-polling for watching keys.

`Twisted Web agent <https://twistedmatrix.com/documents/current/web/howto/client.html>`_ and `treq <https://github.com/twisted/treq>`_ is used for HTTP, and both use a configurable Twisted Web HTTP connection pool.


Limitations
-----------

