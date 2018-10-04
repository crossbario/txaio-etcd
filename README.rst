etcd for Twisted
================

| |Version| |Build Status| |Docs|

**txaioetcd** is an object-relational remote persistant map layer based on etcd.

It also provides a low-level asynchronous API for Twisted applications.


Installation
------------

**etcd version 3.1 or higher** is required. etcd 2 will not work. etcd 3.0 also isn't enough - at least watching keys doesn't work over the gRPC HTTP gateway yet.

The implementation is pure Python code compatible with both **Python 2 and 3**, and runs perfect on **PyPy**.

The library currently requires **Twisted**, though the API was designed to allow adding asyncio support later (PRs are welcome!) with no breakage.

But other than the underlying network library, there are only small pure Python dependencies.

To install txaioetcd

.. code-block:: sh

    pip install txaioetcd


Introduction
------------

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
        def parse(obj):
            """
            Parse a generic host language object into a native object of this class.
            """

Then define a table for a slot to be used with key-value stores:

.. code-block:: python

    # users table schema (a table with UUID keys and CBOR values holding User objects)
    tab_users = pmap.MapUuidCbor(1, marshal=lambda user: user.marshal(), unmarshal=User.parse)

Open a connection to etcd as a backing store:

.. code-block:: python

    db = Database(Client(reactor))
    revision = await db.status()
    print('connected to etcd: revision', revision)

Create a native Python object from our class above and store it in the table, that is remotely in etcd:

.. code-block:: python

    user = User()
    user.name = 'foobar'
    user.oid = uuid.uuid4()

    async with db.begin(write=True) as txn:
        tab_users[txn, user.oid] = user

    print('user stored: {}'.format(user))

Load a native Python object from the table, taht is remotely from etcd:

.. code-block:: python

    user = None

    async with db.begin() as txn:
        user = tab_users[txn, user.oid]

    print('user loaded: {}'.format(user))


Examples
--------

Continue with the tutorial (for the high-level API):

* `Tutorial 1 - Boilerplate <https://github.com/crossbario/txaio-etcd/tree/master/examples/etcdb/tut1.py>`_
* `Tutorial 2 - Insert/Update/Delete Key-Values <https://github.com/crossbario/txaio-etcd/tree/master/examples/etcdb/tut2.py>`_

or checkout the examples for the low-level API:

* `Connecting <https://github.com/crossbario/txaio-etcd/tree/master/examples/connect.py>`_
* `Basic Operations (CRUD) <https://github.com/crossbario/txaio-etcd/tree/master/examples/crud.py>`_
* `Watching keys <https://github.com/crossbario/txaio-etcd/tree/master/examples/watch.py>`_
* `Transactions <https://github.com/crossbario/txaio-etcd/tree/master/examples/transaction.py>`_
* `Leases <https://github.com/crossbario/txaio-etcd/tree/master/examples/lease.py>`_

or the high-level API examples:

* `Database Basic Ops <https://github.com/crossbario/txaio-etcd/tree/master/examples/etcdb/basic.py>`_
* `Database Indexing <https://github.com/crossbario/txaio-etcd/tree/master/examples/etcdb/index.py>`_


.. |Version| image:: https://img.shields.io/pypi/v/txaioetcd.svg
   :target: https://pypi.python.org/pypi/txaioetcd

.. |Build Status| image:: https://travis-ci.org/crossbario/txaio-etcd.svg?branch=master
   :target: https://travis-ci.org/crossbario/txaio-etcd

.. |Docs| image:: https://readthedocs.org/projects/txaio-etcd/badge/?version=latest
   :target: https://txaio-etcd.readthedocs.io/en/latest/
