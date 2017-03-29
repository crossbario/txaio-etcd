txaioetcd - etcd for Twisted
============================

| |Version| |Docs|


`etcd <https://coreos.com/etcd/docs/latest/>`_ is a powerful building block in networked and distributed applications. etcd describes itself as "distributed reliable key-value store for the most critical data of a distributed system".

`Twisted <http://twistedmatrix.com/>`_ is an advanced network framework to implement networked and distributed applications.

Hence the desire for a fully asynchronous etcd v3 Twisted client with broad feature support: **txaioetcd**.

**txaioetcd** currently supports these etcd v3 basic features

- arbitrary byte strings for keys and values
- set and get values by key
- get values by range or prefix
- delete value (by single key, range and prefix)

and the following advanced features

- watch key sets with asynchronous callback
- submit transactions ("multiact")
- create, refresh and revoke leases
- associate key-values with leases

**txaioetcd** also plans to provide abstractions on top of the etcd3 transaction primitive, like for example:

- global locks and sequences
- transactional, multi-consumer-producer queues


Examples
--------

1. `Connecting <https://github.com/crossbario/txaio-etcd/tree/master/examples/connect.py>`_
2. `Basic Operations (CRUD) <https://github.com/crossbario/txaio-etcd/tree/master/examples/crud.py>`_
3. `Watching keys <https://github.com/crossbario/txaio-etcd/tree/master/examples/watch.py>`_
4. `Transactions <https://github.com/crossbario/txaio-etcd/tree/master/examples/transaction.py>`_
5. `Leases <https://github.com/crossbario/txaio-etcd/tree/master/examples/lease.py>`_


Requirements
-------------

**etcd version 3.1 or higher** is required. etcd 2 will not work. etcd 3.0 also isn't enough - at least watching keys doesn't work over the gRPC HTTP gateway yet.

The implementation is pure Python code compatible with both **Python 2 and 3**, and runs perfect on **PyPy**.

The library currently requires **Twisted**, though the API was designed to allow adding asyncio support later (PRs are welcome!) with no breakage.

But other than the underlying network library, there are only small pure Python dependencies.


Installation
------------

To install txaioetcd

.. code-block:: sh

    pip install txaioetcd


etcd
----

Installation
............

To build and install etcd 3.1

.. code-block:: sh

    ETCD_VER=v3.1.0
    DOWNLOAD_URL=https://github.com/coreos/etcd/releases/download
    curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz \
        -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
    sudo mkdir -p /opt/etcd && sudo tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz \
        -C /opt/etcd --strip-components=1

To verify the installation, check the version

.. code-block:: sh

    /opt/etcd/etcd --version

Open a console and start etcd

.. code-block:: sh

    /opt/etcd/etcd

To scratch the etcd database

.. code-block:: sh

    rm -rf ~/default.etcd/


Test using etcdctl
..................

Get cluster status

.. code-block:: sh

    ETCDCTL_API=3 /opt/etcd/etcdctl endpoint -w table status

Set a key

.. code-block:: sh

    ETCDCTL_API=3 /opt/etcd/etcdctl put foo hello

Get a key

.. code-block:: sh

    ETCDCTL_API=3 /opt/etcd/etcdctl get foo

Watch a key

.. code-block:: sh

    ETCDCTL_API=3 /opt/etcd/etcdctl watch foo


Test using curl
...............


Get cluster status

.. code-block:: sh

    curl -L http://localhost:2379/v3alpha/maintenance/status -X POST -d '{}'

Set a key (value "hello" on key "foo" both base64 encoded):

.. code-block:: sh

    curl -L http://localhost:2379/v3alpha/kv/put -X POST -d '{"key": "Zm9v", "value": "YmFy"}'

Get a key ("foo" base64 encoded)

.. code-block:: sh

    curl -L http://localhost:2379/v3alpha/kv/range -X POST -d '{"key": "Zm9v"}'

Watch a key ("foo" base64 encoded)

.. code-block:: sh

    curl -L http://localhost:2379/v3alpha/watch -X POST -d '{"create_request": {"key": "Zm9v"}}'



Usage
-----

Example Client
..............

Here is an example etcd3 client that retrieves the cluster status

.. sourcecode:: python

    from twisted.internet.task import react
    from twisted.internet.defer import inlineCallbacks

    import txaio
    from txaioetcd import Client, KeySet

    @inlineCallbacks
    def main(reactor):
        etcd = Client(reactor, u'http://localhost:2379')

        status = yield etcd.status()
        print(status)

        # insert one of the snippets below HERE

    if __name__ == '__main__':
        txaio.start_logging(level='info')
        react(main)

The following snippets demonstrate the etcd3 features supported by txaioetcd. To run the snippets, use the boilerplate above.


Setting keys
............

**Set** a value for some keys

.. sourcecode:: python

    for i in range(10):
        etcd.set('mykey{}'.format(i).encode(), b'foobar')

Note that both keys and values in etcd3 are arbitrary byte strings.

Whether you use UTF-8 encoded strings with leading slash or anything else does not matter to etcd3. Put differently, there is no semantics associated with slashes on sides of etcd3 whatsoever and slash semantics - if any - is fully up to an application.


Getting keys
............

**Get a value by key** from etcd

.. sourcecode:: python

    result = yield etcd.get(b'mykey')
    if result.kvs:
        kv = result.kvs[0]
        print(kv)
    else:
        print('key not found')

**Iterate** over key **range**

.. sourcecode:: python

    result = yield etcd.get(KeySet(b'mykey1', b'mykey5'))
    for kv in result.kvs:
        print(kv)

**Iterate** over keys with given **prefix**

.. sourcecode:: python

    result = yield etcd.get(KeySet(b'mykey', prefix=True))
    for kv in result.kvs:
        print(kv)

Deleting keys
.............

**Delete** a (single) key

.. sourcecode:: python

    etcd.delete(b'mykey3')

**Delete** set of keys in given range

.. sourcecode:: python

    etcd.delete(KeySet(b'mykey3', b'mykey7'))

**Delete** set of keys with given prefix and **return** previous key-value pairs

.. sourcecode:: python

    deleted = yield etcd.delete(KeySet(b'mykey3'), return_previous=True)
    print('deleted key-value pairs: {}'.format(deleted.previous))


Watching keys
.............

**Watch** keys for changes

.. sourcecode:: python

    # callback invoked for every change
    def on_change(kv):
        print('on_change: {}'.format(kv))

    # start watching on set of keys with given prefix
    d = etcd.watch([KeySet(b'mykey', prefix=True)], on_change)
    print('watching ..')

    # stop after 60 seconds
    yield txaio.sleep(60)
    d.cancel()


Transactions
............

.. sourcecode:: python

    txn = Transaction(
        compare=[
            CompValue(b'mykey1', '==', b'val1')
        ],
        success=[
            OpSet(b'mykey1', b'val2'),
            OpSet(b'mykey2', b'success')
        ],
        failure=[
            OpSet(b'mykey2', b'failure'),
            OpGet(b'mykey1')
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


Leases
......

Write me. For now, please see the lease.py example in the examples folder.


Locks
.....

NO YET IMPLEMENTED (JUST A POSSIBLE SKETCH).

Create or wait to acquire a named lock

.. sourcecode:: python

    lock = yield etcd.lock(b'mylock')

    # now do something on the exclusively locked resource
    # or whatever the lock stands for or is associated with

    lock.release()

Create or wait to acquire, but with a timeout


.. sourcecode:: python

    try:
        lock = yield etcd.lock(b'mylock', timeout=10)
    except Timeout:
        print('could not acquire lock: timeout')
    else:

        # operate on the locked resource

        lock.release()


Design Goals
------------

We want etcd3 support because of the extended, useful functionality and semantics offered.

Supporting etcd2 using a restricted parallel API or by hiding away the differences between etcd2 and etcd3 seems ugly and we didn't needed etcd2 support anyway. So etcd2 support is a non-goal.

The implementation must be fully non-blocking and asynchronous, and must run on Twisted in particular. Supporting asyncio, or even a Python 3.5+ syntax for Twisted etc etc seems possible to add later without affecting the API.

The implementation must run fast on PyPy, which rules out using native code wrapped using cpyext. We also want to avoid native code in general, as it introduces security and memory-leak worries, and PyPy's JIT produces very fast code anyway.


Implementation
--------------

The library uses the `gRPC HTTP gateway <https://coreos.com/etcd/docs/latest/dev-guide/api_grpc_gateway.html>`_ within etcd3 and talks regular HTTP/1.1 with efficient long-polling for watching keys.

`Twisted Web agent <https://twistedmatrix.com/documents/current/web/howto/etcd.html>`_ and `treq <https://github.com/twisted/treq>`_ is used for HTTP, and both use a configurable Twisted Web HTTP connection pool.


Current limitations
-------------------

Missing asyncio support
.......................

The API of txaioetcd was designed not leaking anything from Twisted other than Deferreds. This is similar to and in line with the approach that txaio takes.

The approach will allow us to add an asyncio implementation under the hood without affecting existing application code, but make the library run over either Twisted or asyncio, similar to txaio.

Further, Twisted wants to support the new Python 3.5+ async/await syntax on Twisted Deferreds, and that in turn would make it possible to write applications on top of txaioetcd that work either using native Twisted or asyncio without changing the app code.

Note that this is neither the same as running a Twisted reactor on top of an asyncio loop nor vice versa. The app is still running under Twisted *or* asyncio, but selecting the framework might even be a user settable command line option to the app.


Missing native protocol support
...............................

The implementation talks HTTP/1.1 to the gRPC HTTP gateway of etcd3, and the binary payload is transmitted JSON with string values that Base64 encode the binary values of the etcd3 API.

Likely more effienct would be talk the native protocol of etcd3, which is HTTP/2 and gRPC/protobuf based. The former requires a HTTP/2 Twisted client. The latter requires a pure Python implementation of protobuf messages used and gRPC. So this is definitely some work, and probably premature optimization. The gateway is just way simpler to integrate with as it uses the least common or invasive thing, namely HTTP/REST and long polling. Certainly not the most efficient, that is also true.

But is seems recommended to run a local etcd proxy on each host, and this means we're talking the (ineffcient) HTTP protocol over loopback TCP, and hence it is primarily a question of burning some additional CPU cycles.


Missing dynamic watches
.......................

The HTTP/2 etcd3 native protocol allows to change a created watch on the fly. Maybe the gRPC HTTP gateway also allows that.

But I couldn't get a streaming *request* working with neither Twisted Web agent nor treq. A streaming *response* works of course, as in fact this is how the watch feature in txaioetcd is implemented.

And further, the API of txaioetcd doesn't expose it either. A watch is created, started and a Twisted Deferred (or possibly asyncio Future) is returned. The watch can be stopped by canceling the Deferred (Future) previously returned - but that is it. A watch cannot be changed after the fact.

Regarding the public API of txaioetcd, I think there will be a way that would allow adding dynamic watches that is upward compatible and hence wouldn't break any app code. So it also can be done later.


Asynchronous Iterators
......................

When a larger set of keys and/or values is fetched, it might be beneficial to apply the asynchronous iterator pattern.

This might come in handy on newer Pythons with syntax for that.

Note that a full blown consumer-producer (flow-controller) pattern is probably overkill, as etcd3 isn't for large blobs or media files.


Asynchronous Context Managers
.............................

This would be a nice and robust idiom to write app code in:

.. sourcecode:: python

    async with etcd.lock(b'mylock') as lock:
        # whatever the way this block finishes,
        # the lock will be unlocked


No etcd admin API support
.........................

etcd has a large number of administrative procedures as part of the API like list, add, remove etc cluster members and other things.

These API parts of etcd are currently not exposed in txaioetcd - and I am not completely convinced it would necessary given there is `etcdctl` or even desirable from a security perspective, as it exposes sensitive API at the app level.

But yes, it is missing completely.


.. |Version| image:: https://img.shields.io/pypi/v/txaioetcd.svg
   :target: https://pypi.python.org/pypi/txaioetcd

.. |Docs| image:: https://readthedocs.org/projects/txaio-etcd/badge/?version=latest
   :target: https://txaio-etcd.readthedocs.io/en/latest/
