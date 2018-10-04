Using the etcd Client layer
===========================

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
------------

**Set** a value for some keys

.. sourcecode:: python

    for i in range(10):
        etcd.set('mykey{}'.format(i).encode(), b'foobar')

Note that both keys and values in etcd3 are arbitrary byte strings.

Whether you use UTF-8 encoded strings with leading slash or anything else does not matter to etcd3. Put differently, there is no semantics associated with slashes on sides of etcd3 whatsoever and slash semantics - if any - is fully up to an application.


Getting keys
------------

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
-------------

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
-------------

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
------------

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
------

Write me. For now, please see the lease.py example in the examples folder.


Locks
-----

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
