###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Crossbar.io Technologies GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

from __future__ import absolute_import

import sys
import time
import six

from txaioetcd import _types

# Select the most precise wallclock measurement function available on the platform
if sys.platform.startswith('win'):
    # On Windows, this function returns wall-clock seconds elapsed since the
    # first call to this function, as a floating point number, based on the
    # Win32 function QueryPerformanceCounter(). The resolution is typically
    # better than one microsecond
    walltime = time.clock
    _ = walltime()  # this starts wallclock
else:
    # On Unix-like platforms, this used the first available from this list:
    # (1) gettimeofday() -- resolution in microseconds
    # (2) ftime() -- resolution in milliseconds
    # (3) time() -- resolution in seconds
    walltime = time.time


class DbTransactionStats(object):
    def __init__(self):
        self.puts = 0
        self.dels = 0
        self._started = walltime()

    @property
    def started(self):
        return self._started

    @property
    def duration(self):
        if self._started:
            return walltime() - self._started
        else:
            return 0

    def reset(self):
        self.puts = 0
        self.dels = 0
        self._started = walltime()


# from contextlib import asynccontextmanager
# @asynccontextmanager


class DbTransaction(object):

    PUT = 1
    DEL = 2

    def __init__(self, db, write=False, stats=None, timeout=None):
        """

        :param db: Etcd database instance this transaction is running for.
        :type db: etcd.Database

        :param write: Set True for a transaction that should be allowed write access.
        :type write: bool

        :param stats: Transaction statistics tracked.
        :type stats: etcd.TransactionStats

        :param timeout: Transaction timeout in seconds.
        :type timeout: int
        """
        self._db = db

        self._write = write
        self._stats = stats
        self._timeout = timeout

        self._revision = None
        self._committed = None
        self._buffer = None

    @property
    def revision(self):
        return self._txn_revision

    @property
    def committed(self):
        return self._committed

    async def __aenter__(self):
        assert (self._revision is None)

        status = await self._db._client.status()
        # self._revision = status.header.revision
        self._revision = status
        self._buffer = {}

        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        assert (self._revision is not None)

        # yield etcd.set(b'foo', b'bar'

        # https://docs.python.org/3/reference/datamodel.html#object.__exit__
        # If the context was exited without an exception, all three arguments will be None.
        if exc_type is None:
            if self._buffer:
                ops = []
                for key, (op, data) in self._buffer.items():
                    if op == DbTransaction.PUT:
                        ops.append(_types.OpSet(key, data))
                    elif op == DbTransaction.DEL:
                        ops.append(_types.OpDel(key))
                    else:
                        raise Exception('logic error')

                # this implements an optimistic-concurrency-control (OCC) scheme
                comps = []
                # for key in self._buffer.keys():
                #    # modified revision comparison
                #    comps.append(CompModified(self._txn_revision, '<=', kv.mod_revision))

                # raw etcd transaction
                txn = _types.Transaction(compare=comps, success=ops, failure=[])

                # commit buffered transaction to etcd
                res = await self._db._client.submit(txn, timeout=self._timeout)
                # self._committed = res.header.revision
                self._committed = res
                print(
                    '   >>> TRANSACTION committed successfully: revision={}, committed={}, ops={} <<<'.format(
                        self._revision, self._committed, len(ops)))
            else:
                print('   >>> TRANSACTION committed empty <<<')
        else:
            # transaction aborted: throw away buffered transaction
            print('   >>> TRANSACTION failed! <<<')
            self._committed = -1

        # finally: transaction buffer, but not the transaction revision
        self._buffer = None
        # self._revision = None

    def id(self):
        assert (self._revision is not None)

        return self._txn.id()

    async def get(self, key):
        assert (self._revision is not None)
        if key in self._buffer:
            op, data = self._buffer[key]
            if op == DbTransaction.PUT:
                return data
            elif op == DbTransaction.DEL:
                raise IndexError('no such key')
        else:
            result = await self._db._client.get(key)
            return result
            # if result.kvs:
            #    return result.kvs[0].value

    def put(self, key, data, overwrite=True):
        assert (self._revision is not None)

        self._buffer[key] = (DbTransaction.PUT, data)

        if self._stats:
            self._stats.puts += 1
        return True

    def delete(self, key):
        assert (self._revision is not None)

        self._buffer[key] = (DbTransaction.DEL, None)

        if self._stats:
            self._stats.dels += 1
        return True


class Database(object):
    """

    Notes. The (etcd) Revision is the current revision of etcd. It is incremented every
    time the v3 backed is modified (e.g., Put, Delete, Txn). ModRevision is the etcd
    revision of the last update to a key. Version is the number of times the key
    has been modified since it was created.

    https://github.com/etcd-io/etcd/blob/master/Documentation/learning/data_model.md
    """

    def __init__(self, client, prefix=None, readonly=False):
        assert prefix is None or type(prefix) == six.binary_type
        assert type(readonly) == bool
        self._client = client
        self._prefix = prefix
        self._readonly = readonly

    def begin(self, write=False, stats=None, timeout=None):

        if write and self._readonly:
            raise Exception('database is read-only')

        txn = DbTransaction(db=self, write=write, stats=stats, timeout=timeout)

        return txn

    async def status(self):
        _status = await self._client.status()
        return _status
        # return _status.header.revision

    def stats(self):
        return self._client._stats.marshal()
