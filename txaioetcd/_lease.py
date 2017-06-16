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

from twisted.internet.defer import inlineCallbacks, returnValue

import treq

from txaioetcd._types import Header, Expired


__all__ = (
    'Lease'
)


class Lease(object):
    """
    An etcd lease.

    :ivar header:
    :vartype header:

    :ivar time_to_live:
    :vartype time_to_live:

    :ivar lease_id:
    :vartype lease_id:
    """

    def __init__(self, client, header, time_to_live, lease_id=None):
        self._client = client
        self._expired = False
        self.header = header
        self.time_to_live = time_to_live
        self.lease_id = lease_id

    def __str__(self):
        return u'Lease(client={}, expired={}, header={}, time_to_live={}, lease_id={})'.format(self._client, self._expired, self.header, self.time_to_live, self.lease_id)

    @staticmethod
    def _parse(client, obj):
        # {
        #     'ID': '1780709837822722771',
        #     'TTL': '5',
        #     'header': {
        #         'cluster_id': '12111318200661820288',
        #         'member_id': '13006018358126188726',
        #         'raft_term': '2',
        #         'revision': '119'
        #     }
        # }

        header = Header._parse(obj[u'header']) if u'header' in obj else None
        time_to_live = int(obj[u'TTL'])
        lease_id = int(obj[u'ID'])
        return Lease(client, header, time_to_live, lease_id)

    @inlineCallbacks
    def remaining(self):
        """
        Get the remaining time-to-live of this lease.

        :returns: TTL in seconds.
        :rtype: int
        """
        if self._expired:
            raise Expired()

        obj = {
            u'ID': self.lease_id,
        }
        data = json.dumps(obj).encode('utf8')

        url = u'{}/v3alpha/kv/lease/timetolive'.format(self._client._url).encode()
        response = yield treq.post(url, data, headers=self._client._REQ_HEADERS)

        obj = yield treq.json_content(response)

        ttl = obj.get(u'TTL', None)
        if not ttl:
            self._expired = True
            raise Expired()

        # grantedTTL = int(obj[u'grantedTTL'])
        # header = Header._parse(obj[u'header']) if u'header' in obj else None

        returnValue(ttl)

    @inlineCallbacks
    def keys(self):
        """
        Retrieves keys associated with the lease.

        :returns: The keys.
        :rtype: list of bytes
        """
        if self._expired:
            raise Expired()

        obj = {
            u'ID': self.lease_id,
            u'keys': True
        }
        data = json.dumps(obj).encode('utf8')

        url = u'{}/v3alpha/kv/lease/timetolive'.format(self._client._url).encode()
        response = yield treq.post(url, data, headers=self._client._REQ_HEADERS)

        obj = yield treq.json_content(response)

        ttl = obj.get(u'TTL', None)
        if not ttl:
            self._expired = True
            raise Expired()

        # grantedTTL = int(obj[u'grantedTTL'])
        # header = Header._parse(obj[u'header']) if u'header' in obj else None
        keys = [binascii.a2b_base64(key) for key in obj.get(u'keys', [])]

        returnValue(keys)

    @inlineCallbacks
    def revoke(self):
        """
        Revokes a lease. All keys attached to the lease will expire
        and be deleted.

        :returns: Response header.
        :rtype: instance of :class:`txaioetcd.Header`
        """
        if self._expired:
            raise Expired()

        obj = {
            # ID is the lease ID to revoke. When the ID is revoked, all
            # associated keys will be deleted.
            u'ID': self.lease_id,
        }
        data = json.dumps(obj).encode('utf8')

        url = u'{}/v3alpha/kv/lease/revoke'.format(self._client._url).encode()
        response = yield treq.post(url, data, headers=self._client._REQ_HEADERS)

        obj = yield treq.json_content(response)

        header = Header._parse(obj[u'header']) if u'header' in obj else None

        self._expired = True

        returnValue(header)

    @inlineCallbacks
    def refresh(self):
        """
        Keeps the lease alive by streaming keep alive requests from the client
        to the server and streaming keep alive responses from the server to
        the client.

        :returns: Response header.
        :rtype: instance of :class:`txaioetcd.Header`
        """
        if self._expired:
            raise Expired()

        obj = {
            # ID is the lease ID for the lease to keep alive.
            u'ID': self.lease_id,
        }
        data = json.dumps(obj).encode('utf8')

        url = u'{}/v3alpha/lease/keepalive'.format(self._client._url).encode()
        response = yield treq.post(url, data, headers=self._client._REQ_HEADERS)

        obj = yield treq.json_content(response)

        if u'result' not in obj:
            raise Exception('bogus lease refresh response (missing "result") in {}'.format(obj))

        ttl = obj[u'result'].get(u'TTL', None)
        if not ttl:
            self._expired = True
            raise Expired()

        header = Header._parse(obj[u'result'][u'header']) if u'header' in obj[u'result'] else None

        self._expired = False

        returnValue(header)
