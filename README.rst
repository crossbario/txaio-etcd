etcd for Twisted
================

| |Version| |Build Status| |Docs|

**txaioetcd** is an *object-relational remote persistant map layer* backed by etcd.

It also provides a low-level asynchronous API for general Twisted etcd applications, bypassing
the object-relational layer of the library.


Installation
------------

The implementation is pure Python code compatible with both **Python 2 and 3**
and runs perfect on **PyPy**.
On the server-side, **etcd version 3.1 or higher** is required. To install txaioetcd

.. code-block:: sh

    pip install txaioetcd

.. note::

    The library currently requires **Twisted**, though the API was designed to allow adding asyncio support later (PRs are welcome!) with no breakage.
    But other than the underlying network library, there are only small pure Python dependencies.
    etcd 2 will not work. etcd 3.0 also isn't enough - at least watching keys doesn't work over the gRPC HTTP gateway yet.


Getting Started
---------------

Get the complete example source code for the getting started below from
`here <https://github.com/crossbario/txaio-etcd/tree/master/examples/etcdb/tut2.py>`_.

To start with **txaioetcd** using the high-level, remote persistent map API,
define at least one class for data to be persisted,
eg a `User class <https://github.com/crossbario/txaio-etcd/tree/master/examples/etcdb/user.py>`_:

.. code-block:: python

    class User(object):

        def marshal(self):
            """
            Marshal the object into a generic host language object.
            """

        @staticmethod
        def unmarshal(obj):
            """
            Parse a generic host language object into a native object of this class.
            """

Then define a table for a slot to be used with key-value stores:

.. code-block:: python

    from txaioetcd import pmap

    # users table schema (a table with UUID keys and CBOR values holding User objects)
    tab_users = pmap.MapUuidCbor(1, marshal=lambda user: user.marshal(), unmarshal=User.unmarshal)

Above will define a table slot (with index 1) that has UUIDs for keys, and CBOR serialized
objects of User class for values.

.. note::

    The User class does not appear literally, but only the "marshal" and "unmarshal"
    parameters to the persistant map type specifies the object interface of the user class
    to the persistant map library. The application developers needs to provide implementations of
    the respective application class marshal/unmarshal interface.

The available types for keys and values of persistant maps include:

* String (UTF8), eg ``MapUuidString``, ``MapStringString``, ``MapStringUuid``, ..
* Binary, eg ``MapUuidBinary``, ``MapStringBinary``, ..
* OID (uint64), eg ``MapUuidOid``, ``MapOidCbor``, ..
* UUID (uint128), eg ``MapUuidCbor``, ``MapUuidUuid``, ..
* JSON, eg ``MapUuidJson``, ``MapOidJson``, ``MapStringJson``, ..
* CBOR, eg ``MapOidCbor``, ``MapUuidCbor``, ``MapStringCbor``, ..
* Pickle (Python), eg ``MapStringPickle``, ..
* Flatbuffers, eg ``MapUuidFlatbuffers``, ..

For example, the following is another valid slot definition:

.. code-block:: python

    # users table schema (a table with OID keys and Python Pickle values holding User objects)
    tab_users = pmap.MapOidPickle(2, marshal=lambda user: user.marshal(), unmarshal=User.parse)

Above will define a table slot (with index 2) that has OIDs for keys, and Python Pickle serialized
objects of User class for values.

Connecting
..........

First open a connection to etcd as a backing store:

.. code-block:: python

    from txaioetcd import Client, Database

    etcd = Client(reactor, url='http://localhost:2379')
    db = Database(etcd)

To check the database connection:

.. code-block:: python

    revision = await db.status()
    print('connected to etcd: revision', revision)


Storing and loading objects
...........................

Now create a native Python object from the class above and store it in the table, that is remotely in etcd:

.. code-block:: python

    user = User()
    user.name = 'foobar'
    user.oid = uuid.uuid4()

    # create an async writable transaction to modify etcd data
    async with db.begin(write=True) as txn:
        tab_users[txn, user.oid] = user

    # data is committed when transaction leaves scope .. here
    print('user stored: {}'.format(user))

Load a native Python object from the table, that is remotely from etcd:

.. code-block:: python

    # create an async read-only transaction when only accessing data in etcd
    async with db.begin() as txn:
        user = await tab_users[txn, user.oid]
        print('user loaded: {}'.format(user))


Putting it together
...................

To put all the pieces together and run the code, you might use the following boilerplate

.. code-block:: python

    import txaio
    txaio.use_twisted()

    from twisted.internet.task import react
    from twisted.internet.defer import ensureDeferred

    from txaioetcd import Client, Database

    async def main(reactor):
        etcd = Client(reactor, url='http://localhost:2379')
        db = Database()
        revision = await db.status()
        print('connected to etcd: revision', revision)

        # INSERT YOUR CODE HERE

    def _main():
        return react(
            lambda reactor: ensureDeferred(
                main(reactor)
            )
        )

    if __name__ == '__main__':
        txaio.start_logging(level='info')
        _main()

Insert your code to operate on etcd in above placeholder.


.. |Version| image:: https://img.shields.io/pypi/v/txaioetcd.svg
   :target: https://pypi.python.org/pypi/txaioetcd

.. |Build Status| image:: https://travis-ci.org/crossbario/txaio-etcd.svg?branch=master
   :target: https://travis-ci.org/crossbario/txaio-etcd

.. |Docs| image:: https://readthedocs.org/projects/txaio-etcd/badge/?version=latest
   :target: https://txaio-etcd.readthedocs.io/en/latest/
