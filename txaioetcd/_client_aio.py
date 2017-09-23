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

import aiohttp

from txaioetcd import Status, Deleted, Revision, \
    Failed, Success, Range, Lease
from txaioetcd import _client_commons as commons

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
        assembler = commons.StatusRequestAssembler(self._url)

        obj = await self._post(assembler.url, assembler.data, timeout)

        return Status._parse(obj)

    async def set(self, key, value, lease=None, return_previous=None, timeout=None):
        assembler = commons.PutRequestAssembler(self._url, key, value, lease, return_previous)

        obj = await self._post(assembler.url, assembler.data, timeout)

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
        assembler = commons.GetRequestAssembler(self._url, key, range_end)

        obj = await self._post(assembler.url, assembler.data, timeout)

        return Range._parse(obj)

    async def delete(self, key, return_previous=None, timeout=None):
        assembler = commons.DeleteRequestAssembler(self._url, key, return_previous)

        obj = await self._post(assembler.url, assembler.data, timeout)

        return Deleted._parse(obj)

    async def watch(self, keys, on_watch, start_revision=None, timeout=None):
        raise Exception('not implemented')

    async def submit(self, txn, timeout=None):
        url = commons.ENDPOINT_SUBMIT.format(self._url).encode()
        data = txn._marshal()

        obj = await self._post(url, data, timeout)

        header, responses = commons.validate_client_submit_response(obj)

        if obj.get(u'succeeded', False):
            return Success(header, responses)
        else:
            raise Failed(header, responses)

    async def lease(self, time_to_live, lease_id=None, timeout=None):
        assembler = commons.LeaseRequestAssembler(self._url, time_to_live, lease_id)

        obj = await self._post(assembler.url, assembler.data, timeout)

        return Lease._parse(self, obj)
