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

import json
import binascii

import six

import txaio
txaio.use_twisted()

from twisted.internet.defer import Deferred, succeed, inlineCallbacks, returnValue, CancelledError
from twisted.internet import protocol
from twisted.web.client import Agent, HTTPConnectionPool
from twisted.web.iweb import IBodyProducer, UNKNOWN_LENGTH
from twisted.web.http_headers import Headers

import treq

from txetcd3.types import Value, Header, Status, Deleted

__all__ = (
    'Client',
)


def _increment_last_byte(byte_string):
    """
    Increment a byte string by 1 - this is used for etcd prefix gets/watches.

    FIXME: This is fun is doing it wrong when the last octet equals 0xFF.
    """
    s = bytearray(byte_string)
    s[-1] = s[-1] + 1
    return bytes(s)


class _BufferedSender(object):
    """
    HTTP buffered request sender for use with Twisted Web agent.
    """

    length = UNKNOWN_LENGTH

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class _BufferedReceiver(protocol.Protocol):
    """
    HTTP buffered response receiver for use with Twisted Web agent.
    """
    def __init__(self, done):
        self._buf = []
        self._done = done

    def dataReceived(self, data):
        self._buf.append(data)

    def connectionLost(self, reason):
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
        self._buf = b''
        self._cb = cb
        self._done = done

    def dataReceived(self, data):
        self._buf += data
        while True:
            i = self._buf.find(self.SEP)
            if i > 0:
                data = self._buf[:i]
                try:
                    obj = json.loads(data.decode('utf8'))
                except Exception as e:
                    self.log.warn('JSON parsing of etcd streaming response from failed: {}'.format(e))
                else:
                    for evt in obj[u'result'].get(u'events', []):
                        if u'kv' in evt:
                            d = evt[u'kv']

                            key = binascii.a2b_base64(d[u'key'])
                            value = binascii.a2b_base64(d[u'value'])

                            version = d[u'version']
                            create_revision = d[u'create_revision']
                            mod_revision = d[u'mod_revision']

                            try:
                                self._cb(key, Value(value, version=version, create_revision=create_revision, mod_revision=mod_revision))
                            except Exception as e:
                                self.log.warn('exception raised from etcd watch callback {} swallowed: {}'.format(self._cb, e))

                self._buf = self._buf[i + len(self.SEP):]
            else:
                break

    def connectionLost(self, reason):
        # FIXME: test if reason is twisted.web.client.ResponseDone, if not, do an errback
        if self._done:
            self._done.callback(reason)
            self._done = None


class Client(object):
    """
    etcd client that talks to the gRPC HTTP gateway endpoint of etcd v3.

    TODO:
        * /v3alpha/kv/deleterange
        * /v3alpha/kv/txn
        * /v3alpha/lease/grant
        * /v3alpha/lease/keepalive
        * /v3alpha/kv/lease/revoke
        * /v3alpha/kv/lease/timetolive

    See: https://coreos.com/etcd/docs/latest/dev-guide/apispec/swagger/rpc.swagger.json
    """

    log = txaio.make_logger()

    REQ_HEADERS = {
        'Content-Type': ['application/json']
    }
    """
    Default request headers for HTTP/POST requests issued to the
    gRPC HTTP gateway endpoint of etcd.
    """

    def __init__(self, reactor, url, pool=None):
        """

        :param rector: Twisted reactor to use.
        :type reactor: class
        :param url: etcd URL, eg `http://localhost:2379`
        :type url: str
        :param pool: Twisted Web agent connection pool
        :type pool:
        """
        if type(url) != six.text_type:
            raise TypeError('url must be of type unicode, was {}'.format(type(url)))
        self._url = url
        self._pool = pool or HTTPConnectionPool(reactor, persistent=True)
        self._agent = Agent(reactor, connectTimeout=10, pool=self._pool)

    @inlineCallbacks
    def status(self):
        """
        Get etcd status.

        URL:     /v3alpha/maintenance/status
        """
        url = u'{}/v3alpha/maintenance/status'.format(self._url).encode()
        obj = {
            # yes, we must provide an empty dict for the request!
        }
        data = json.dumps(obj).encode('utf8')

        response = yield treq.post(url, data, headers=self.REQ_HEADERS)
        obj = yield treq.json_content(response)

        status = Status.parse(obj)

        returnValue(status)

    @inlineCallbacks
    def delete(self, key, range_end=None, prev_kv=False):
        """
        Delete value(s) from etcd.

        URL:     /v3alpha/kv/deleterange

        :param key: key is the first key to delete in the range.
        :type key: bytes
        :param range_end: range_end is the key following the last key to delete
            for the range [key, range_end).\nIf range_end is not given, the range
            is defined to contain only the key argument.\nIf range_end is one bit
            larger than the given key, then the range is all keys with the prefix
            (the given key).\nIf range_end is '\\0', the range is all keys greater
            than or equal to the key argument.
        :key range_end: bytes
        :param prev_kv: If prev_kv is set, etcd gets the previous key-value pairs
            before deleting it.\nThe previous key-value pairs will be returned in the
            delete response.
        :key prev_kv: bool
        """
        url = u'{}/v3alpha/kv/deleterange'.format(self._url).encode()
        obj = {
            u'key': binascii.b2a_base64(key).decode(),
            u'range_end': binascii.b2a_base64(range_end).decode() if range_end else None,
            u'prev_kv': prev_kv
        }
        data = json.dumps(obj).encode('utf8')

        response = yield treq.post(url, data, headers=self.REQ_HEADERS)
        obj = yield treq.json_content(response)
        res = Deleted.parse(obj)

        returnValue(res)

    @inlineCallbacks
    def set(self, key, value, lease=None, prev_kv=None):
        """
        Put puts the given key into the key-value store.

        A put request increments the revision of the key-value
        store and generates one event in the event history.

        URL:     /v3alpha/kv/put

        :param key: key is the key, in bytes, to put into the key-value store.
        :type key: bytes
        :param lease: lease is the lease ID to associate with the key in the key-value store. A lease\nvalue of 0 indicates no lease.
        :type lease: int
        :param prev_kv: If prev_kv is set, etcd gets the previous key-value pair before changing it.\nThe previous key-value pair will be returned in the put response.
        :type prev_kv: bool
        :param value: value is the value, in bytes, to associate with the key in the key-value store.
        :key value: bytes
        """
        url = u'{}/v3alpha/kv/put'.format(self._url).encode()
        obj = {
            u'key': binascii.b2a_base64(key).decode(),
            u'value': binascii.b2a_base64(value).decode()
        }
        data = json.dumps(obj).encode('utf8')

        response = yield treq.post(url, data, headers=self.REQ_HEADERS)
        obj = yield treq.json_content(response)

        revision = obj[u'header'][u'revision']
        returnValue(revision)

    @inlineCallbacks
    def get(self, key, range_end=None, prefix=None):
        """
        Range gets the keys in the range from the key-value store.

        URL:    /v3alpha/kv/range

        :param key: key is the first key for the range. If range_end is not given, the request only looks up key.
        :type key: bytes

        :param range_end: range_end is the upper bound on the requested range
            [key, range_end).\nIf range_end is '\\0', the range is all keys \u003e= key.
            If the range_end is one bit larger than the given key, then the range requests
            get the all keys with the prefix (the given key).\nIf both key and range_end
            are '\\0', then range requests returns all keys.
        :type range_end: bytes

        :param prefix: If set, and no range_end is given, compute range_end from key prefix.
        :type prefix: bool

        :param count_only: count_only when set returns only the count of the keys in the range.
        :type count_only: bool

        :param keys_only: keys_only when set returns only the keys and not the values.
        :type keys_only: bool

        :param limit: limit is a limit on the number of keys returned for the request.
        :type limit: int

        :param max_create_revision: max_create_revision is the upper bound for returned key create revisions; all keys with\ngreater create revisions will be filtered away.
        :type max_create_revision: int

        :param max_mod_revision: max_mod_revision is the upper bound for returned key mod revisions; all keys with\ngreater mod revisions will be filtered away.
        :type max_mod_revision: int

        :param min_create_revision: min_create_revision is the lower bound for returned key create revisions; all keys with\nlesser create trevisions will be filtered away.
        :type min_create_revision: int

        :param min_mod_revision: min_mod_revision is the lower bound for returned key mod revisions; all keys with\nlesser mod revisions will be filtered away.
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
            exchange for possible stale reads,\na serializable range request is served
            locally without needing to reach consensus\nwith other nodes in the cluster.
        :type serializable: bool

        :param sort_order:
        :type sort_order:

        :param sort_target:
        :type sort_taget:
        """
        url = u'{}/v3alpha/kv/range'.format(self._url).encode()
        obj = {
            u'key': binascii.b2a_base64(key).decode()
        }
        if not range_end and prefix is True:
            range_end = _increment_last_byte(key)
        if range_end:
            obj[u'range_end'] = binascii.b2a_base64(range_end).decode()
        data = json.dumps(obj).encode('utf8')

        response = yield treq.post(url, data, headers=self.REQ_HEADERS)
        obj = yield treq.json_content(response)

        count = int(obj.get(u'count', 0))
        if count == 0:
            raise IndexError('no such key')
        else:
            if count > 1:
                values = {}
                for kv in obj[u'kvs']:
                    key = binascii.a2b_base64(kv[u'key'])
                    value = binascii.a2b_base64(kv[u'value'])
                    mod_revision = int(kv[u'mod_revision'])
                    create_revision = int(kv[u'create_revision'])
                    version = int(kv[u'version'])
                    values[key] = Value(value, version=version, create_revision=create_revision, mod_revision=mod_revision)
                returnValue(values)
            else:
                kv = obj[u'kvs'][0]
                value = binascii.a2b_base64(kv[u'value'])
                mod_revision = int(kv[u'mod_revision'])
                create_revision = int(kv[u'create_revision'])
                version = int(kv[u'version'])
                value = Value(value, version=version, create_revision=create_revision, mod_revision=mod_revision)
                returnValue(value)

    def watch(self, prefixes, on_watch, start_revision=None):
        """
        Watch one or more key prefixes and invoke a callback.

        Watch watches for events happening or that have happened. The entire event
        history can be watched starting from the last compaction revision.

        URL:     /v3alpha/watch

        :param prefixes: The prefixes to watch.
        :type prefixes: list of bytes
        :param on_watch: The callback to invoke upon receiving a watch event.
        :type on_watch: callable
        :param start_revision: start_revision is an optional revision to watch
            from (inclusive). No start_revision is \"now\".
        :type start_revision: int
        """
        d = self._start_watching(prefixes, on_watch, start_revision)

        def on_err(err):
            if isinstance(err.value, CancelledError):
                # swallow canceling!
                pass
            else:
                return err

        d.addErrback(on_err)

        return d

    def _start_watching(self, prefixes, on_watch, start_revision):
        data = []
        headers = dict()
        url = u'{}/v3alpha/watch'.format(self._url).encode()

        # create watches for all key prefixes
        for key in prefixes:
            range_end = _increment_last_byte(key)
            obj = {
                'create_request': {
                    u'start_revision': start_revision,
                    u'key': binascii.b2a_base64(key).decode(),

                    # range_end is the end of the range [key, range_end) to watch.
                    # If range_end is not given,\nonly the key argument is watched.
                    # If range_end is equal to '\\0', all keys greater than nor equal
                    # to the key argument are watched. If the range_end is one bit
                    # larger than the given key,\nthen all keys with the prefix (the
                    # given key) will be watched.
                    u'range_end': binascii.b2a_base64(range_end).decode(),

                    # progress_notify is set so that the etcd server will periodically
                    # send a WatchResponse with\nno events to the new watcher if there
                    # are no recent events. It is useful when clients wish to recover
                    # a disconnected watcher starting from a recent known revision.
                    # The etcd server may decide how often it will send notifications
                    # based on current load.
                    u'progress_notify': True,
                }
            }
            data.append(json.dumps(obj).encode('utf8'))

        data = b'\n'.join(data)

        # HTTP/POST request in one go, but response is streaming ..
        d = self._agent.request(b'POST',
                                url,
                                Headers(headers),
                                _BufferedSender(data))

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

    def submit(self, txn):
        """
        Submit a etcd transaction.
        """
        pass