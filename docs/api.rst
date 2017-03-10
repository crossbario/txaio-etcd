API Reference
=============

Client
------

.. autoclass:: txaioetcd.Client
    :members:
    :undoc-members:
    :special-members: __init__


KeySet
------

.. autoclass:: txaioetcd.KeySet
    :members:
    :undoc-members:
    :special-members: __init__


KeyValue
--------

.. autoclass:: txaioetcd.KeyValue
    :members:


Helpers
-------

Instances of the following classes are created by ``txaio-etcd``, and returned to app code:


.. autoclass:: txaioetcd.Header
    :members:
    :undoc-members:

.. autoclass:: txaioetcd.Status
    :members:
    :undoc-members:

.. autoclass:: txaioetcd.Range
    :members:
    :undoc-members:

.. autoclass:: txaioetcd.Revision
    :members:
    :undoc-members:

.. autoclass:: txaioetcd.Deleted
    :members:
    :undoc-members:

.. autoclass:: txaioetcd.Lease
    :members:
    :undoc-members:


Errors
------

Exception instances of the following classes are created and raised by ``txaio-etcd``:


.. autoclass:: txaioetcd.Error
    :members:
    :undoc-members:

.. autoclass:: txaioetcd.Failed
    :members:
    :undoc-members:

.. autoclass:: txaioetcd.Success
    :members:
    :undoc-members:

.. autoclass:: txaioetcd.Expired
    :members:
    :undoc-members:



Transaction
-----------

Instances of the following classes are created by app code, and provided to the ``txaio-etcd``:

.. autoclass:: txaioetcd.Transaction
    :members:
    :undoc-members:
    :special-members: __init__


Transaction Comparisons
-----------------------

Instances of the following classes are created by app code, and provided to the ``txaio-etcd``:

.. autoclass:: txaioetcd.Comp
    :members:
    :undoc-members:
    :special-members: __init__

.. autoclass:: txaioetcd.CompValue
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

.. autoclass:: txaioetcd.CompVersion
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

.. autoclass:: txaioetcd.CompCreated
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

.. autoclass:: txaioetcd.CompModified
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__


Transaction Operations
----------------------

Instances of the following classes are created by app code, and provided to the ``txaio-etcd``:

.. autoclass:: txaioetcd.Op
    :members:
    :undoc-members:
    :special-members: __init__

.. autoclass:: txaioetcd.OpGet
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

.. autoclass:: txaioetcd.OpSet
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__

.. autoclass:: txaioetcd.OpDel
    :members:
    :undoc-members:
    :show-inheritance:
    :special-members: __init__
