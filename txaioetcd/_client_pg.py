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

from psycopg2 import Binary
from psycopg2.extras import Json

import txaio
txaio.use_twisted()  # noqa

from twisted.internet.defer import inlineCallbacks
from twisted.enterprise import adbapi

__all__ = ('Client', )


class ClientStats(object):
    log = txaio.make_logger()

    def __init__(self):
        self.reset()

    def reset(self):
        self._posts_by_url = {}

    def marshal(self):
        obj = {'posts': self._posts_by_url}
        return obj

    def log_post(self, url, data, timeout):
        url = url.decode('utf8')
        if url not in self._posts_by_url:
            self._posts_by_url[url] = 0
        self._posts_by_url[url] += 1


class Client(object):
    """

    docker run --name postgres -e POSTGRES_PASSWORD=postgres -d postgres
    docker run -it --rm --name postgres -e POSTGRES_PASSWORD=postgres -d postgres
    """

    log = txaio.make_logger()
    """
    Logger object.
    """

    _REQ_HEADERS = {'Content-Type': ['application/json']}
    """
    Default request headers for HTTP/POST requests issued to the
    gRPC HTTP gateway endpoint of etcd.
    """

    def __init__(self,
                 reactor,
                 pool=None,
                 host='127.0.0.1',
                 port=5432,
                 database='postgres',
                 user='postgres',
                 password='postgres'):
        """

        :param rector: Twisted reactor to use.
        :type reactor: class
        """
        self._stats = ClientStats()

        if not pool:
            # create a new database connection pool. connections are created lazy (as needed)
            #
            def on_pool_connection(conn):
                # callback fired when Twisted adds a new database connection to the pool.
                # use this to do any app specific configuration / setup on the connection
                pid = conn.get_backend_pid()
                print('New psycopg2 connection created (backend PID={})'.format(pid))

            pool = adbapi.ConnectionPool(
                'psycopg2',
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                cp_min=3,
                cp_max=10,
                cp_noisy=True,
                cp_openfun=on_pool_connection,
                cp_reconnect=True,
                cp_good_sql='SELECT 1')

        self._pool = pool

    def stats(self):
        return self._stats.marshal()

    def status(self, timeout=None):
        """
        Get etcd status.

        :param timeout: Request timeout in seconds.
        :type timeout: int

        :returns: The current etcd cluster status.
        :rtype: instance of :class:`txaioetcd.Status`
        """

        def run(txn):
            txn.execute("SELECT now()")
            rows = txn.fetchall()
            res = "{0}".format(rows[0][0])
            return res

        return self._pool.runInteraction(run)

    @inlineCallbacks
    def set(self, key, value, lease=None, return_previous=None, timeout=None):
        """
        Set the value for the key in the key-value store.

        Setting a value on a key increments the revision
        of the key-value store and generates one event in
        the event history.

        :param key: key is the key, in bytes, to put into
            the key-value store.
        :type key: bytes

        :param value: value is the value, in bytes, to
            associate with the key in the key-value store.
        :key value: bytes

        :param lease: Lease to associate the key in the
            key-value store with.
        :type lease: instance of :class:`txaioetcd.Lease` or None

        :param return_previous: If set, return the previous key-value.
        :type return_previous: bool or None

        :param timeout: Request timeout in seconds.
        :type timeout: int

        :returns: Revision info
        :rtype: instance of :class:`txaioetcd.Revision`
        """
        raise NotImplementedError()

    def get(self,
            key,
            range_end=None,
            count_only=None,
            keys_only=None,
            limit=None,
            max_create_revision=None,
            min_create_revision=None,
            min_mod_revision=None,
            revision=None,
            serializable=None,
            sort_order=None,
            sort_target=None,
            timeout=None):
        """
        Range gets the keys in the range from the key-value store.

        :param key: key is the first key for the range. If range_end is not given,
            the request only looks up key.
        :type key: bytes

        :param range_end: range_end is the upper bound on the requested range
            [key, range_end). If range_end is ``\\0``, the range is all keys ``\u003e=`` key.
            If the range_end is one bit larger than the given key, then the range requests
            get the all keys with the prefix (the given key). If both key and range_end
            are ``\\0``, then range requests returns all keys.
        :type range_end: bytes

        :param prefix: If set, and no range_end is given, compute range_end from key prefix.
        :type prefix: bool

        :param count_only: count_only when set returns only the count of the keys in the range.
        :type count_only: bool

        :param keys_only: keys_only when set returns only the keys and not the values.
        :type keys_only: bool

        :param limit: limit is a limit on the number of keys returned for the request.
        :type limit: int

        :param max_create_revision: max_create_revision is the upper bound for returned
            key create revisions; all keys with greater create revisions will be filtered away.
        :type max_create_revision: int

        :param max_mod_revision: max_mod_revision is the upper bound for returned key
            mod revisions; all keys with greater mod revisions will be filtered away.
        :type max_mod_revision: int

        :param min_create_revision: min_create_revision is the lower bound for returned
            key create revisions; all keys with lesser create trevisions will be filtered away.
        :type min_create_revision: int

        :param min_mod_revision: min_mod_revision is the lower bound for returned key
            mod revisions; all keys with lesser mod revisions will be filtered away.
        :type min_min_revision: int

        :param revision: revision is the point-in-time of the key-value store to use for the
            range. If revision is less or equal to zero, the range is over the newest
            key-value store. If the revision has been compacted, ErrCompacted is returned as
            a response.
        :type revision: int

        :param serializable: serializable sets the range request to use serializable
            member-local reads. Range requests are linearizable by default; linearizable
            requests have higher latency and lower throughput than serializable requests
            but reflect the current consensus of the cluster. For better performance, in
            exchange for possible stale reads, a serializable range request is served
            locally without needing to reach consensus with other nodes in the cluster.
        :type serializable: bool

        :param sort_order: Sort order for returned KVs,
            one of :class:`txaioetcd.OpGet.SORT_ORDERS`.
        :type sort_order: str

        :param sort_target: Sort target for sorting returned KVs,
            one of :class:`txaioetcd.OpGet.SORT_TARGETS`.
        :type sort_taget: str or None

        :param timeout: Request timeout in seconds.
        :type timeout: int or None
        """

        def run(pg_txn):
            pg_txn.execute("SELECT pgetcd.get(%s,%s)", (Binary(key), 10))
            rows = pg_txn.fetchall()
            res = "{0}".format(rows[0][0])
            return res

        return self._pool.runInteraction(run)

    @inlineCallbacks
    def delete(self, key, return_previous=None, timeout=None):
        """
        Delete value(s) from etcd.

        :param key: key is the first key to delete in the range.
        :type key: bytes or instance of :class:`txaioetcd.KeySet`

        :param return_previous: If enabled, return the deleted key-value pairs
        :type return_previous: bool or None

        :param timeout: Request timeout in seconds.
        :type timeout: int

        :returns: Deletion info
        :rtype: instance of :class:`txaioetcd.Deleted`
        """
        raise NotImplementedError()

    def watch(self, keys, on_watch, filters=None, start_revision=None, return_previous=None):
        """
        Watch one or more keys or key sets and invoke a callback.

        Watch watches for events happening or that have happened. The entire event history
        can be watched starting from the last compaction revision.

        :param keys: Watch these keys / key sets.
        :type keys: list of bytes or list of instance of :class:`txaioetcd.KeySet`

        :param on_watch: The callback to invoke upon receiving
            a watch event.
        :type on_watch: callable

        :param filters: Any filters to apply.

        :param start_revision: start_revision is an optional
            revision to watch from (inclusive). No start_revision is "now".
        :type start_revision: int

        :param return_previous: Flag to request returning previous values.

        :returns: A deferred that just fires when watching has started successfully,
            or which fires with an error in case the watching could not be started.
        :rtype: twisted.internet.Deferred
        """
        raise NotImplementedError()

    def submit(self, txn, timeout=None):
        """
        Submit a transaction.

        Processes multiple requests in a single transaction.
        A transaction increments the revision of the key-value store
        and generates events with the same revision for every
        completed request.

        It is not allowed to modify the same key several times
        within one transaction.

        From google paxosdb paper:

        Our implementation hinges around a powerful primitive which
        we call MultiOp. All other database operations except for
        iteration are implemented as a single call to MultiOp.
        A MultiOp is applied atomically and consists of three components:

        1. A list of tests called guard. Each test in guard checks
           a single entry in the database. It may check for the absence
           or presence of a value, or compare with a given value.
           Two different tests in the guard may apply to the same or
           different entries in the database. All tests in the guard
           are applied and MultiOp returns the results. If all tests
           are true, MultiOp executes t op (see item 2 below), otherwise
           it executes f op (see item 3 below).

        2. A list of database operations called t op. Each operation in
           the list is either an insert, delete, or lookup operation, and
           applies to a single database entry. Two different operations
           in the list may apply to the same or different entries in
           the database. These operations are executed if guard evaluates
           to true.

        3. A list of database operations called f op. Like t op, but
           executed if guard evaluates to false.

        :param txn: The transaction to submit.
        :type txn: instance of :class:`txaioetcd.Transaction`

        :param timeout: Request timeout in seconds.
        :type timeout: int

        :returns: An instance of :class:`txaioetcd.Success` or an exception
            of :class:`txioetcd.Failed` or :class:`txaioetcd.Error`
        :rtype: instance of :class:`txaioetcd.Success`,
            :class:`txaioetcd.Failed` or :class:`txaioetcd.Error`
        """

        def run(pg_txn):
            val = Json(txn._marshal())
            pg_txn.execute("SELECT pgetcd.submit(%s,%s)", (val, 10))
            rows = pg_txn.fetchall()
            res = "{0}".format(rows[0][0])
            return res

        return self._pool.runInteraction(run)

    @inlineCallbacks
    def lease(self, time_to_live, lease_id=None, timeout=None):
        """
        Creates a lease which expires if the server does not
        receive a keep alive within a given time to live period.

        All keys attached to the lease will be expired and deleted if
        the lease expires.

        Each expired key generates a delete event in the event history.

        :param time_to_live: TTL is the advisory time-to-live in seconds.
        :type time_to_live: int

        :param lease_id: ID is the requested ID for the lease.
            If ID is None, the lessor (etcd) chooses an ID.
        :type lease_id: int or None

        :param timeout: Request timeout in seconds.
        :type timeout: int

        :returns: A lease object representing the created lease. This
            can be used for refreshing or revoking the least etc.
        :rtype: instance of :class:`txaioetcd.Lease`
        """
        raise NotImplementedError()
