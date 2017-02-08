txetcd3
=======

`etcd3 <https://coreos.com/etcd/docs/latest/>`_ is a powerful building block in networked and distributed applications, which `Twisted <http://twistedmatrix.com/>`_ is an advanced substrate to implement in turn.

Hence the need for a fully asynchronous etcd3 Twisted client with broad feature support: **txetcd3**.

Currently supported features:

- set and get values by bkey
- arbitrary byte strings for keys and values
- get values by range or prefix
- delete value (by single key, range and prefix)
- watch key sets with asynchronous callback
- create, refresh and delete leases
- submit transactions


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

The following will create an etcd3 client, retrieve the cluster status and exit

.. sourcecode:: python

    from twisted.internet.task import react
    from twisted.internet.defer import inlineCallbacks
    import txetcd3
    import txaio

    @inlineCallbacks
    def main(reactor):
        client = txetcd3.Client(reactor, u'http://localhost:2379')

        status = yield client.status()
        print(status)

        # insert one of the snippets below HERE

    if __name__ == '__main__':
        txaio.start_logging(level='info')
        react(main)

Snippets
........

The following snippets demonstrate the etcd3 features supported by txetcd3. To run the snippets, use the boilerplate above.

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

    pairs = yield client.get(txetcd3.KeySet(b'/foo1', b'/foo5'))
    for key, value in pairs.items():
        print('key={}: {}'.format(key, value))

**Iterate** over keys with given **prefix**

.. sourcecode:: python

    pairs = yield client.get(txetcd3.KeySet(b'/foo', prefix=True))
    for key, value in pairs.items():
        print('key={}: {}'.format(key, value))

**Set** a value for some keys

.. sourcecode:: python

    for i in range(10):
        client.set('/foo{}'.format(i).encode(), b'woa;)')

**Delete** a (single) key

.. sourcecode:: python

    client.delete(b'/foo3')

**Delete** set of keys in given range

.. sourcecode:: python

    client.delete(txetcd3.KeySet(b'/foo3', b'/foo7'))

**Delete** set of keys with given prefix and return previous key-value pairs

.. sourcecode:: python

    deleted = yield client.delete(txetcd3.KeySet(b'/foo3'), return_previous=True)
    print('deleted key-value pairs: {}'.format(deleted))

**Watch** keys for changes

.. sourcecode:: python

    # callback invoked for every change
    def on_change(key, value):
        print('watch callback fired for key {}: {}'.format(key, value))

    # start watching on set of keys with given prefix
    d = client.watch([txetcd3.KeySet(b'/foo', prefix=True)], on_change)
    print('watching ..')

    # stop after 10 seconds
    yield sleep(10)
    d.cancel()


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

