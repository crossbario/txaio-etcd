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
import struct
import uuid
from pprint import pformat

import six
import cbor2

import txaio
from txaioetcd import _types, _pmap

# from typing import Optional, List

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

txaio.use_twisted()


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


class DbTransaction(object):

    PUT = 1
    DEL = 2

    log = txaio.make_logger()

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

    def id(self):
        assert (self._revision is not None)

        return self._revision

    @property
    def revision(self):
        assert (self._revision is not None)

        return self._txn_revision

    @property
    def committed(self):
        assert (self._revision is not None)
        return self._committed

    async def __aenter__(self):
        assert (self._revision is None)

        status = await self._db._client.status()
        self._revision = status.header.revision
        self._buffer = {}

        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        assert (self._revision is not None)

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

                self.log.info(
                    'from revision {from_revision}: tx commit (rev={revision}, commit={committed}, ops={ops})',
                    from_revision=self._revision,
                    revision=self._revision,
                    committed=self._committed,
                    ops=len(ops))  # noqa
            else:
                self.log.info(
                    'from revision {from_revision}: transaction committed (empty)',
                    from_revision=self._revision)
        else:
            # transaction aborted: throw away buffered transaction
            self.log.info('transaction aborted')
            self._committed = -1

        # finally: transaction buffer, but not the transaction revision
        self._buffer = None

    async def get(self, key, range_end=None, keys_only=None):
        assert (self._revision is not None)

        if range_end is None and key in self._buffer:
            op, data = self._buffer[key]
            if op == DbTransaction.PUT:
                return data
            elif op == DbTransaction.DEL:
                return None
        else:
            result = await self._db._client.get(key, range_end=range_end, keys_only=keys_only)
            if result.kvs:
                self.log.debug(
                    'etcd from key {from_key} to {to_key}: loaded {cnt} records',
                    from_key=key,
                    to_key=range_end,
                    cnt=len(result.kvs))
                if range_end:
                    return result.kvs
                else:
                    return result.kvs[0].value

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


class ConfigurationElement(object):

    # oid: uuid.UUID
    # name: str
    # description: Optional[str]
    # tags: Optional[List[str]]

    def __init__(self, oid=None, name=None, description=None, tags=None):
        self._oid = oid
        self._name = name
        self._description = description
        self._tags = tags

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if other.oid != self.oid:
            return False
        if other.name != self.name:
            return False
        if other.description != self.description:
            return False
        if (self.tags and not other.tags) or (not self.tags and other.tags):
            return False
        if other.tags and self.tags:
            if set(other.tags) ^ set(self.tags):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def oid(self):
        return self._oid

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def tags(self):
        return self._tags

    def marshal(self):
        value = {
            u'oid': str(self._oid),
            u'name': self._name,
        }
        if self.description:
            value[u'description'] = self._description
        if self.tags:
            value[u'tags'] = self._tags
        return value

    @staticmethod
    def parse(value):
        assert type(value) == dict
        oid = value.get('oid', None)
        if oid:
            oid = uuid.UUID(oid)
        obj = ConfigurationElement(
            oid=oid,
            name=value.get('name', None),
            description=value.get('description', None),
            tags=value.get('tags', None))
        return obj


class Slot(ConfigurationElement):
    def __init__(self, oid=None, name=None, description=None, tags=None, slot=None, creator=None):
        ConfigurationElement.__init__(self, oid=oid, name=name, description=description, tags=tags)
        self._slot = slot
        self._creator = creator

    def __str__(self):
        return pformat(self.marshal())

    @property
    def creator(self):
        return self._creator

    @property
    def slot(self):
        return self._slot

    def marshal(self):
        obj = ConfigurationElement.marshal(self)
        obj.update({
            'creator': self._creator,
            'slot': self._slot,
        })
        return obj

    @staticmethod
    def parse(data):
        assert type(data) == dict

        obj = ConfigurationElement.parse(data)

        slot = data.get('slot', None)
        creator = data.get('creator', None)

        drvd_obj = Slot(
            oid=obj.oid,
            name=obj.name,
            description=obj.description,
            tags=obj.tags,
            slot=slot,
            creator=creator)
        return drvd_obj


class Database(object):
    """

    Notes. The (etcd) Revision is the current revision of etcd. It is incremented every
    time the v3 backed is modified (e.g., Put, Delete, Txn). ModRevision is the etcd
    revision of the last update to a key. Version is the number of times the key
    has been modified since it was created.

    https://github.com/etcd-io/etcd/blob/master/Documentation/learning/data_model.md
    """
    log = txaio.make_logger()

    def __init__(self, client, prefix=None, readonly=False):
        """

        :param client:
        :param prefix:
        :param readonly:
        """
        assert prefix is None or type(prefix) == six.binary_type
        assert type(readonly) == bool
        self._client = client
        self._prefix = prefix
        self._readonly = readonly
        self._slots = None
        self._slots_by_index = None

    async def status(self):
        """

        :return:
        """
        _status = await self._client.status()
        return _status.header.revision

    async def _cache_slots(self):
        slots = {}
        slots_by_index = {}
        result = await self._client.get(_types.KeySet(b'\0\0', prefix=True))
        for kv in result.kvs:
            if kv.key and len(kv.key) >= 4:
                slot_index = struct.unpack('>H', kv.key[2:4])[0]
                assert kv.value
                slot = Slot.parse(cbor2.loads(kv.value))
                assert slot.slot == slot_index
                slots[slot.oid] = slot
                slots_by_index[slot.oid] = slot_index
        self._slots = slots
        self._slots_by_index = slots_by_index

    async def _get_slots(self, cached=True):
        """

        :param cached:
        :return:
        """
        if self._slots is None or not cached:
            await self._cache_slots()
        return self._slots

    async def _get_free_slot(self):
        """

        :param cached:
        :return:
        """
        slot_indexes = sorted(self._slots_by_index.values())
        if len(slot_indexes) > 0:
            return slot_indexes[-1] + 1
        else:
            return 1

    async def _set_slot(self, slot_index, slot):
        """

        :param slot_index:
        :param meta:
        :return:
        """
        assert type(slot_index) in six.integer_types
        assert slot_index > 0 and slot_index < 65536
        assert slot is None or isinstance(slot, Slot)

        if slot:
            assert slot_index == slot.slot

        key = b'\0\0' + struct.pack('>H', slot_index)
        if slot:
            obj = slot.marshal()
            data = cbor2.dumps(obj)

        if not slot:
            result = await self._client.get(key)
            if result.kvs:
                slot = result.kvs[0]
                await self._client.delete(key)
                if slot.oid in self._slots:
                    del self._slots[slot.oid]
                if slot.oid in self._slots_by_index:
                    del self._slots_by_index[slot.oid]
                print('deleted metadata')

        if slot:
            await self._client.set(key, data)
            self._slots[slot.oid] = slot
            self._slots_by_index[slot.oid] = slot_index
            print('wrote metadata for {} to slot {}'.format(slot.oid, slot_index))

    async def attach_slot(self,
                          oid,
                          klass,
                          marshal=None,
                          unmarshal=None,
                          create=True,
                          name=None,
                          description=None):
        """

        :param slot:
        :param klass:
        :param marshal:
        :param unmarshal:
        :return:
        """
        assert isinstance(oid, uuid.UUID)
        assert issubclass(klass, _pmap.PersistentMap)
        assert marshal is None or callable(marshal)
        assert unmarshal is None or callable(unmarshal)
        assert type(create) == bool
        assert name is None or type(name) == six.text_type
        assert description is None or type(description) == six.text_type

        await self._get_slots()

        if oid not in self._slots_by_index:
            print('no slot for persistant map of oid {} found'.format(oid))
            if create:
                slot_index = await self._get_free_slot()
                slot = Slot(oid=oid, creator='unknown', slot=slot_index, name=name, description=description)
                print('allocating slot {} for persistant map {} ..'.format(slot_index, oid))
                await self._set_slot(slot_index, slot)
            else:
                raise Exception('no slot with persistant map of oid {} found'.format(oid))
        else:
            slot_index = self._slots_by_index[oid]
            print('persistant map of oid {} found in slot {}'.format(oid, slot_index))

        if marshal:
            slot_pmap = klass(slot_index, marshal=marshal, unmarshal=unmarshal)
        else:
            slot_pmap = klass(slot_index)

        return slot_pmap

    def stats(self):
        """

        :return:
        """
        return self._client._stats.marshal()

    def begin(self, write=False, stats=None, timeout=None):
        """

        :param write:
        :param stats:
        :param timeout:
        :return:
        """
        if write and self._readonly:
            raise Exception('database is read-only')

        txn = DbTransaction(db=self, write=write, stats=stats, timeout=timeout)

        return txn
