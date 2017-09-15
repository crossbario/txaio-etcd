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

from txaioetcd import Status, Deleted, Revision, \
    Failed, Success, Range, Lease
from txaioetcd._client_commons import (
    validate_client_set_parameters,
    validate_client_get_parameters,
    validate_client_delete_parameters,
    validate_client_lease_parameters,
    validate_client_submit_response,
)

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

    async def _post(self, url, data, timeout):
        response = await self._session.post(url, json=data, timeout=timeout)
        return await response.json()

    async def status(self, timeout=None):
        url = u'{}/v3alpha/maintenance/status'.format(self._url)
        return Status._parse(await self._post(url, {}, timeout))

    async def set(self, key, value, lease=None, return_previous=None, timeout=None):
        validate_client_set_parameters(key, value, lease, return_previous)

        url = u'{}/v3alpha/kv/put'.format(self._url)
        data = {
            u'key': base64.b64encode(key).decode(),
            u'value': base64.b64encode(value).decode()
        }
        if return_previous:
            data[u'prev_kv'] = True
        if lease and lease.lease_id:
            data[u'lease'] = lease.lease_id

        return Revision._parse(await self._post(url, data, timeout))

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
        key, range_end = validate_client_get_parameters(key, range_end)

        url = u'{}/v3alpha/kv/range'.format(self._url)
        data = {
            u'key': base64.b64encode(key.key).decode()
        }
        if range_end:
            data[u'range_end'] = base64.b64encode(range_end).decode()

        return Range._parse(await self._post(url, data, timeout))

    async def delete(self, key, return_previous=None, timeout=None):
        key, range_end = validate_client_delete_parameters(key, return_previous)

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

        return Deleted._parse(await self._post(url, data, timeout))

    async def watch(self, keys, on_watch, start_revision=None, timeout=None):
        raise Exception('not implemented')

    async def submit(self, txn, timeout=None):
        url = u'{}/v3alpha/kv/txn'.format(self._url).encode()
        data = txn._marshal()

        obj = await self._post(url, data, timeout)

        header, responses = validate_client_submit_response(obj)

        if obj.get(u'succeeded', False):
            return Success(header, responses)
        else:
            raise Failed(header, responses)

    async def lease(self, time_to_live, lease_id=None, timeout=None):
        validate_client_lease_parameters(time_to_live, lease_id)

        data = {
            u'TTL': time_to_live,
            u'ID': lease_id or 0,
        }

        url = u'{}/v3alpha/lease/grant'.format(self._url)

        return Lease._parse(self, await self._post(url, data, timeout))
