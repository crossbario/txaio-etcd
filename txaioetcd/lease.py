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

from twisted.internet.defer import inlineCallbacks, returnValue

import treq

from txaioetcd.types import Header, Expired


__all__ = (
    'Lease'
)


class Lease(object):
    """

    * /v3alpha/lease/keepalive
    * /v3alpha/kv/lease/revoke
    * /v3alpha/kv/lease/timetolive
    """

    def __init__(self, client, header, time_to_live, lease_id=None):
        self._client = client
        self.header = header
        self.time_to_live = time_to_live
        self.lease_id = lease_id

    def __str__(self):
        return u'Lease(client={}, header={}, time_to_live={}, lease_id={})'.format(self._client, self.header, self.time_to_live, self.lease_id)

    @staticmethod
    def parse(client, obj):
        """
        Parse object and create instance.

        .. code-block:: json

            {'ID': '1780709837822722771',
             'TTL': '5',
             'header': {'cluster_id': '12111318200661820288',
                        'member_id': '13006018358126188726',
                        'raft_term': '2',
                        'revision': '119'}}
        """
        header = Header.parse(obj[u'header']) if u'header' in obj else None
        time_to_live = int(obj[u'TTL'])
        lease_id = int(obj[u'ID'])
        return Lease(client, header, time_to_live, lease_id)

    @inlineCallbacks
    def refresh(self):
        """

        URL: /v3alpha/lease/keepalive
        """
        obj = {
            # ID is the lease ID for the lease to keep alive.
            u'ID': self.lease_id,
        }
        data = json.dumps(obj).encode('utf8')

        url = u'{}/v3alpha/lease/keepalive'.format(self._client._url).encode()
        response = yield treq.post(url, data, headers=self._client.REQ_HEADERS)

        obj = yield treq.json_content(response)

        #from pprint import pprint
        #pprint(obj)

        # {'result': {'ID': '1780709837822722795',
        #             'TTL': '5',
        #             'header': {'cluster_id': '12111318200661820288',
        #                        'member_id': '13006018358126188726',
        #                        'raft_term': '2',
        #                        'revision': '119'}}}

        if u'result' not in obj:
            raise Exception('bogus lease refresh response (missing "result") in {}'.format(obj))

        ttl = obj[u'result'].get(u'TTL', None)
        if not ttl:
            raise Expired()

        header = Header.parse(obj[u'result'][u'header']) if u'header' in obj[u'result'] else None

        returnValue(header)
