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
