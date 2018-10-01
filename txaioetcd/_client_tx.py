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

import os
import json
import base64

import six

import txaio
txaio.use_twisted()  # noqa

from twisted.internet.defer import Deferred, succeed, inlineCallbacks, returnValue, CancelledError
from twisted.internet import protocol
from twisted.web.client import Agent, HTTPConnectionPool
from twisted.web.iweb import UNKNOWN_LENGTH
from twisted.web.http_headers import Headers

import treq

from txaioetcd import KeySet, KeyValue, Status, Deleted, \
    Revision, Failed, Success, Range, Lease

from txaioetcd._types import _increment_last_byte
from txaioetcd import _client_commons as commons
from txaioetcd._client_commons import (
    validate_client_submit_response,
    ENDPOINT_WATCH,
    ENDPOINT_SUBMIT,
)

__all__ = ('Client', )


class _BufferedSender(object):
    """
    HTTP buffered request sender for use with Twisted Web agent.
    """

    length = UNKNOWN_LENGTH

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):  # noqa
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):  # noqa
        pass

    def stopProducing(self):  # noqa
        pass


class _BufferedReceiver(protocol.Protocol):
    """
    HTTP buffered response receiver for use with Twisted Web agent.
    """

    def __init__(self, done):
        self._buf = []
        self._done = done

    def dataReceived(self, data):  # noqa
        self._buf.append(data)

    def connectionLost(self, reason):  # noqa
        # TODO: test if reason is twisted.web.client.ResponseDone, if not, do an errback
        if self._done:
            self._done.callback(b''.join(self._buf))
            self._done = None


class _StreamingReceiver(protocol.Protocol):
    """
    HTTP streaming response receiver for use with Twisted Web agent.
    """

    log = txaio.make_logger()

    SEP = b'\x0a'
    """
    A streaming response from the gRPC HTTP gateway of etcd3 will send
    JSON pieces separated by "newline".

    The exact separator used probably depends on the platform where
    etcd3 (the server) runs - not sure. But Unix newline works for me now.
    """

    def __init__(self, cb, done=None):
        """
        :param cb: Callback to fire upon a JSON chunk being received and parsed.
        :type cb: callable

        :param done: Deferred to fire when done.
        :type done: t.i.d.Deferred
        """
        self._cb = cb
        self._done = done

    def dataReceived(self, data):  # noqa
        for msg in data.split(self.SEP):
            try:
                obj = json.loads(msg.decode('utf8'))
            except Exception as e:
                self.log.warn('JSON parsing of etcd streaming response from failed: {}'.format(e))
            else:
                for evt in obj[u'result'].get(u'events', []):
                    if u'kv' in evt:
                        kv = KeyValue._parse(evt[u'kv'])
                        try:
                            self._cb(kv)
                        except Exception as e:
                            self.log.warn('exception raised from etcd watch callback {} swallowed: {}'.format(
                                self._cb, e))

    #   ODD: Trying to use a parameter instead of *args errors out as soon as the
    #        parameter is accessed.
    #
    #   The check for errors to ignore (Cancelled) is handled further up the chain ..

    def connectionLost(self, *args):  # noqa
        if self._done:
            self._done.callback(args[0])
            self._done = None


class _None(object):
    pass


class Client(object):
    """
    etcd Twisted client that talks to the gRPC HTTP gateway endpoint of etcd v3.

    See: https://coreos.com/etcd/docs/latest/dev-guide/apispec/swagger/rpc.swagger.json
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

    def __init__(self, reactor, url=None, pool=None, timeout=None, connect_timeout=None):
        """

        :param rector: Twisted reactor to use.
        :type reactor: class

        :param url: etcd URL, eg `http://localhost:2379`
        :type url: str

        :param pool: Twisted Web agent connection pool
        :type pool:

        :param timeout: If given, a global request timeout used for all
            requests to etcd.
        :type timeout: float or None

        :param connect_timeout: If given, a global connection timeout used when
            opening a new HTTP connection to etcd.
        :type connect_timeout: float or None
        """
        if url is not None and type(url) != six.text_type:
            raise TypeError('url must be of type unicode, was {}'.format(type(url)))
        self._url = url or os.environ.get(u'ETCD_URL', u'http://localhost:2379')
        self._timeout = timeout
        self._pool = pool or HTTPConnectionPool(reactor, persistent=True)
        self._pool._factory.noisy = False
        self._agent = Agent(reactor, connectTimeout=connect_timeout, pool=self._pool)

    @inlineCallbacks
    def _post(self, url, data, timeout):
        response = yield treq.post(url, json=data, timeout=(timeout or self._timeout))
        json_data = yield treq.json_content(response)
        returnValue(json_data)

    @inlineCallbacks
    def status(self, timeout=None):
        """
        Get etcd status.

        :param timeout: Request timeout in seconds.
        :type timeout: int

        :returns: The current etcd cluster status.
        :rtype: instance of :class:`txaioetcd.Status`
        """
        assembler = commons.StatusRequestAssembler(self._url)

        obj = yield self._post(assembler.url, assembler.data, timeout)

        status = Status._parse(obj)

        returnValue(status)

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
        assembler = commons.PutRequestAssembler(self._url, key, value, lease, return_previous)

        obj = yield self._post(assembler.url, assembler.data, timeout)

        revision = Revision._parse(obj)

        returnValue(revision)

    @inlineCallbacks
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
        assembler = commons.GetRequestAssembler(self._url, key, range_end)

        obj = yield self._post(assembler.url, assembler.data, timeout)

        result = Range._parse(obj)

        returnValue(result)

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
        assembler = commons.DeleteRequestAssembler(self._url, key, return_previous)

        obj = yield self._post(assembler.url, assembler.data, timeout)

        deleted = Deleted._parse(obj)

        returnValue(deleted)

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
        d = self._start_watching(keys, on_watch, filters, start_revision, return_previous)

        #
        #   ODD: Trying to use a parameter instead of *args errors out as soon as the
        #        parameter is accessed.
        #
        def on_err(*args):
            if args[0].type != CancelledError:
                self.log.warn('Watch terminated with "{error}"', error=args[0].type)
                return args[0]

        d.addErrback(on_err)
        return d

    def _start_watching(self, keys, on_watch, filters, start_revision, return_previous):
        data = []
        headers = dict()
        url = ENDPOINT_WATCH.format(self._url).encode()

        # create watches for all key prefixes
        for key in keys:
            if type(key) == six.binary_type:
                key = KeySet(key)
            elif isinstance(key, KeySet):
                pass
            else:
                raise TypeError('key must be binary string or KeySet, not {}'.format(type(key)))

            if key.type == KeySet._SINGLE:
                range_end = None
            elif key.type == KeySet._PREFIX:
                range_end = _increment_last_byte(key.key)
            elif key.type == KeySet._RANGE:
                range_end = key.range_end
            else:
                raise Exception('logic error')

            obj = {
                'create_request': {
                    u'start_revision': start_revision,
                    u'key': base64.b64encode(key.key).decode(),

                    # range_end is the end of the range [key, range_end) to watch.
                    # If range_end is not given,\nonly the key argument is watched.
                    # If range_end is equal to '\\0', all keys greater than nor equal
                    # to the key argument are watched. If the range_end is one bit
                    # larger than the given key,\nthen all keys with the prefix (the
                    # given key) will be watched.

                    # progress_notify is set so that the etcd server will periodically
                    # send a WatchResponse with\nno events to the new watcher if there
                    # are no recent events. It is useful when clients wish to recover
                    # a disconnected watcher starting from a recent known revision.
                    # The etcd server may decide how often it will send notifications
                    # based on current load.
                    u'progress_notify': True,
                }
            }
            if range_end:
                obj[u'create_request'][u'range_end'] = base64.b64encode(range_end).decode()

            if filters:
                obj[u'create_request'][u'filters'] = filters

            if return_previous:
                # If prev_kv is set, created watcher gets the previous KV
                # before the event happens.
                # If the previous KV is already compacted, nothing will be
                # returned.
                obj[u'create_request'][u'prev_kv'] = True

            data.append(json.dumps(obj).encode('utf8'))

        data = b'\n'.join(data)

        # HTTP/POST request in one go, but response is streaming ..
        d = self._agent.request(b'POST', url, Headers(headers), _BufferedSender(data))

        def handle_response(response):
            if response.code == 200:
                done = Deferred()
                response.deliverBody(_StreamingReceiver(on_watch, done))
                return done
            else:
                raise Exception('unexpected response status {}'.format(response.code))

        def handle_error(err):
            self.log.warn('could not start watching on etcd: {error}', error=err.value)
            return err

        d.addCallbacks(handle_response, handle_error)
        return d

    @inlineCallbacks
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
        url = ENDPOINT_SUBMIT.format(self._url).encode()
        data = txn._marshal()

        obj = yield self._post(url, data, timeout)

        header, responses = validate_client_submit_response(obj)

        if obj.get(u'succeeded', False):
            returnValue(Success(header, responses))
        else:
            raise Failed(header, responses)

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
        assembler = commons.LeaseRequestAssembler(self._url, time_to_live, lease_id)

        obj = yield self._post(assembler.url, assembler.data, timeout)

        lease = Lease._parse(self, obj)

        returnValue(lease)
