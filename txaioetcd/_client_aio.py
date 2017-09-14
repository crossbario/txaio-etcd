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

import base64

import aiohttp

from txaioetcd import KeySet, KeyValue, Header, Status, Deleted, \
    Revision, Error, Failed, Success, Range, Lease
from txaioetcd._types import _increment_last_byte

import txaio
txaio.use_asyncio()


__all__ = (
    'Client',
)


class Client:
    """
    etcd asyncio client that talks to the gRPC HTTP gateway endpoint of etcd v3.

    See: https://coreos.com/etcd/docs/latest/dev-guide/apispec/swagger/rpc.swagger.json
    """

    def __init__(self, url, timeout=None):
        self._url = url
        self._session = aiohttp.ClientSession()
        self._timeout = timeout

    async def status(self, timeout=None):
        url = u'{}/v3alpha/maintenance/status'.format(self._url)
        response = await self._session.post(url, json={}, timeout=timeout)
        obj = await response.json()
        return Status._parse(obj)

    async def set(self, key, value, lease=None, return_previous=None, timeout=None):
        if type(key) != bytes:
            raise TypeError('key must be bytes, not {}'.format(type(key)))

        if type(value) != bytes:
            raise TypeError('value must be bytes, not {}'.format(type(value)))

        if lease is not None and not isinstance(lease, Lease):
            raise TypeError('lease must be a Lease object, not {}'.format(type(lease)))

        if return_previous is not None and type(return_previous) != bool:
            raise TypeError('return_previous must be bool, not {}'.format(type(return_previous)))

        url = u'{}/v3alpha/kv/put'.format(self._url)
        data = {
            u'key': base64.b64encode(key).decode(),
            u'value': base64.b64encode(value).decode()
        }
        if return_previous:
            data[u'prev_kv'] = True
        if lease and lease.lease_id:
            data[u'lease'] = lease.lease_id

        response = await self._session.post(url, json=data, timeout=timeout or self._timeout)
        obj = await response.json()

        return Revision._parse(obj)

    async def get(self,
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
        if type(key) == bytes:
            if range_end:
                key = KeySet(key, range_end=range_end)
            else:
                key = KeySet(key)
        elif isinstance(key, KeySet):
            pass
        else:
            raise TypeError('key must either be bytes or a KeySet object, not {}'.format(type(key)))

        if key.type == KeySet._SINGLE:
            range_end = None
        elif key.type == KeySet._PREFIX:
            range_end = _increment_last_byte(key.key)
        elif key.type == KeySet._RANGE:
            range_end = key.range_end
        else:
            raise Exception('logic error')

        url = u'{}/v3alpha/kv/range'.format(self._url)
        data = {
            u'key': base64.b64encode(key.key).decode()
        }
        if range_end:
            data[u'range_end'] = base64.b64encode(range_end).decode()

        response = await self._session.post(url, json=data, timeout=timeout or self._timeout)
        obj = await response.json()
        return Range._parse(obj)

    async def delete(self, key, return_previous=None, timeout=None):
        if type(key) == bytes:
            key = KeySet(key)
        elif isinstance(key, KeySet):
            pass
        else:
            raise TypeError('key must either be bytes or a KeySet object, not {}'.format(type(key)))

        if return_previous is not None and type(return_previous) != bool:
            raise TypeError('return_previous must be bool, not {}'.format(type(return_previous)))

        if key.type == KeySet._SINGLE:
            range_end = None
        elif key.type == KeySet._PREFIX:
            range_end = _increment_last_byte(key.key)
        elif key.type == KeySet._RANGE:
            range_end = key.range_end
        else:
            raise Exception('logic error')

        url = u'{}/v3alpha/kv/deleterange'.format(self._url)
        data = {
            u'key': base64.b64encode(key.key).decode(),
        }
        if range_end:
            # range_end is the key following the last key to delete
            # for the range [key, range_end).
            # If range_end is not given, the range is defined to contain only
            # the key argument.
            # If range_end is one bit larger than the given key, then the range
            # is all keys with the prefix (the given key).
            # If range_end is '\\0', the range is all keys greater
            # than or equal to the key argument.
            #
            data[u'range_end'] = base64.b64encode(range_end).decode()

        if return_previous:
            # If prev_kv is set, etcd gets the previous key-value pairs
            # before deleting it.
            # The previous key-value pairs will be returned in the
            # delete response.
            #
            data[u'prev_kv'] = True

        response = await self._session.post(url, json=data, timeout=timeout or self._timeout)
        obj = await response.json()
        return Deleted._parse(obj)

    async def watch(self, keys, on_watch, start_revision=None, timeout=None):
        raise Exception('not implemented')

    async def submit(self, txn, timeout=None):
        url = u'{}/v3alpha/kv/txn'.format(self._url).encode()
        data = txn._marshal()

        response = await self._session.post(url, json=data, timeout=timeout or self._timeout)
        obj = await response.json()

        if u'error' in obj:
            error = Error._parse(obj)
            raise error

        if u'header' in obj:
            header = Header._parse(obj[u'header'])
        else:
            header = None

        responses = []
        for r in obj.get(u'responses', []):
            if len(r.keys()) != 1:
                raise Exception(
                    'bogus transaction response (multiple response tags in item): {}'.format(obj))

            first = list(r.keys())[0]

            if first == u'response_put':
                re = Revision._parse(r[u'response_put'])
            elif first == u'response_delete_range':
                re = Deleted._parse(r[u'response_delete_range'])
            elif first == u'response_range':
                re = Range._parse(r[u'response_range'])
            else:
                raise Exception('response item "{}" bogus or not implemented'.format(first))

            responses.append(re)

        if obj.get(u'succeeded', False):
            return Success(header, responses)
        else:
            raise Failed(header, responses)

    async def lease(self, time_to_live, lease_id=None, timeout=None):
        if lease_id is not None and type(lease_id) not in int:
            raise TypeError('lease_id must be integer, not {}'.format(type(lease_id)))

        if type(time_to_live) not in int:
            raise TypeError('time_to_live must be integer, not {}'.format(type(time_to_live)))

        if time_to_live < 1:
            raise TypeError('time_to_live must >= 1 second, was {}'.format(time_to_live))

        data = {
            u'TTL': time_to_live,
            u'ID': lease_id or 0,
        }

        url = u'{}/v3alpha/lease/grant'.format(self._url)

        response = await self._session.post(url, json=data, timeout=timeout or self._timeout)
        obj = await response.json()
        return Lease._parse(self, obj)
