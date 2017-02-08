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


Design Goals
------------

We want etcd3 support because of the extended, useful functionality and semantics offered.

Supporting etcd2 using a restricted parallel API or by hiding away the differences between etcd2 and etcd3 seems ugly and we didn't needed etcd2 support anyway. So etcd2 support is a non-goal.

The implementation must be fully non-blocking and asynchronous, and must run on Twisted in particular.

The implementation must run fast on PyPy, which rules out using native code wrapped using cpyext. We also want to avoid native code in general, as it introduces security and memory-leak worries, and PyPy's JIT produces very fast code anyway.


Implementation
--------------

The library uses the gRPC HTTP gateway inside etcd3 and will talk over regular HTTP/1.1, with efficient long-polling for watching keys.


Limitations
-----------

