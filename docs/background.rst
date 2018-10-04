Background
----------

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

- support running on asyncio
- global locks and sequences
- transactional, multi-consumer-producer queues abstraction




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
