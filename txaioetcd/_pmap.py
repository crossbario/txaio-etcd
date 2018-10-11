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

import struct
import sys
import zlib

import six

from zlmdb import _types
from txaioetcd._database import DbTransaction

try:
    import snappy
except ImportError:
    HAS_SNAPPY = False
else:
    HAS_SNAPPY = True

if sys.version_info < (3, ):
    from UserDict import DictMixin as MutableMapping
    _NATIVE_PICKLE_PROTOCOL = 2
else:
    from collections.abc import MutableMapping
    _NATIVE_PICKLE_PROTOCOL = 4


class PersistentMapIterator(object):
    def __init__(self, txn, pmap, from_key=None, to_key=None, return_keys=True, return_values=True):
        self._txn = txn
        self._pmap = pmap

        self._from_key = struct.pack('>H', pmap._slot)
        if from_key:
            self._from_key += pmap._serialize_key(from_key)

        if to_key:
            self._to_key = struct.pack('>H', pmap._slot) + pmap._serialize_key(to_key)
        else:
            self._to_key = struct.pack('>H', pmap._slot + 1)

        self._return_keys = return_keys
        self._return_values = return_values

        self._cursor = None
        self._found = None

    def __iter__(self):
        self._cursor = self._txn._txn.cursor()
        self._found = self._cursor.set_range(self._from_key)
        return self

    def __next__(self):
        if not self._found:
            raise StopIteration

        _key = self._cursor.key()
        if _key >= self._to_key:
            raise StopIteration

        _key = self._pmap._deserialize_key(_key[2:])

        if self._return_values:
            _data = self._cursor.value()
            if _data:
                if self._pmap._decompress:
                    _data = self._pmap._decompress(_data)
                _data = self._pmap._deserialize_value(_data)
        else:
            _data = None

        self._found = self._cursor.next()

        if self._return_keys and self._return_values:
            return _key, _data
        elif self._return_values:
            return _data
        elif self._return_keys:
            return _key
        else:
            return None

    next = __next__  # Python 2


class Index(object):
    def __init__(self, fkey, pmap):
        self._fkey = fkey
        self._pmap = pmap

    @property
    def fkey(self):
        return self._fkey

    @property
    def pmap(self):
        return self._pmap


class PersistentMap(MutableMapping):
    """
    Abstract base class for persistent maps stored in LMDB.
    """
    COMPRESS_ZLIB = 1
    COMPRESS_SNAPPY = 2

    def __init__(self, slot, compress=None):
        """

        :param slot:
        :param compress:
        """
        assert slot is None or type(slot) in six.integer_types
        assert compress is None or compress in [PersistentMap.COMPRESS_ZLIB, PersistentMap.COMPRESS_SNAPPY]

        self._slot = slot

        if compress:
            if compress not in [PersistentMap.COMPRESS_ZLIB, PersistentMap.COMPRESS_SNAPPY]:
                raise Exception('invalid compression mode')
            if compress == PersistentMap.COMPRESS_SNAPPY and not HAS_SNAPPY:
                raise Exception('snappy compression requested, but snappy is not installed')
            if compress == PersistentMap.COMPRESS_ZLIB:
                self._compress = zlib.compress
                self._decompress = zlib.decompress
            elif compress == PersistentMap.COMPRESS_SNAPPY:
                self._compress = snappy.compress
                self._decompress = snappy.uncompress
            else:
                raise Exception('logic error')
        else:
            self._compress = lambda data: data
            self._decompress = lambda data: data

        self._indexes = set()

    def __str__(self):
        return '{}(slot={})'.format(self.__class__, self._slot)

    @property
    def slot(self):
        return self._slot

    def attach_index(self, pmap, fkey):
        """

        :param pmap:
        :param fkey:
        :return:
        """
        assert isinstance(pmap, PersistentMap)
        assert callable(fkey)

        index = Index(fkey, pmap)
        self._indexes.add(index)

        return index

    def detach_index(self, index):
        """

        :param index:
        :return:
        """
        assert isinstance(index, Index)

        if index in self._indexes:
            self._indexes.remove(index)
            return True
        else:
            return False

    def _serialize_key(self, key):
        raise Exception('must be implemented in derived class')

    def _deserialize_key(self, data):
        raise Exception('must be implemented in derived class')

    def _serialize_value(self, value):
        raise Exception('must be implemented in derived class')

    def _deserialize_value(self, data):
        raise Exception('must be implemented in derived class')

    async def __getitem__(self, txn_key):
        """

        :param txn_key:
        :return:
        """
        assert type(txn_key) == tuple and len(txn_key) == 2
        txn, key = txn_key

        _key = struct.pack('>H', self._slot) + self._serialize_key(key)
        _data = await txn.get(_key)

        if _data:
            if self._decompress:
                _data = self._decompress(_data)
            return self._deserialize_value(_data)
        else:
            return None

    def __setitem__(self, txn_key, value):
        """

        :param txn_key:
        :param value:
        :return:
        """
        assert type(txn_key) == tuple and len(txn_key) == 2

        txn, key = txn_key

        assert isinstance(txn, DbTransaction)
        assert key

        _key = struct.pack('>H', self._slot) + self._serialize_key(key)
        _data = self._serialize_value(value)

        if self._compress:
            _data = self._compress(_data)

        txn.put(_key, _data)

        for index in self._indexes:
            # FIXME: remove index entries for previous value

            # add index entries for new value
            _key = struct.pack('>H', index.pmap._slot) + index.pmap._serialize_key(index.fkey(value))
            _data = index.pmap._serialize_value(key)
            txn.put(_key, _data)

            print('DB INDEX PUT:', index, key, _key, _data)

    def __delitem__(self, txn_key):
        """

        :param txn_key:
        :return:
        """
        assert type(txn_key) == tuple and len(txn_key) == 2

        txn, key = txn_key

        _key = struct.pack('>H', self._slot) + self._serialize_key(key)

        txn.delete(_key)

    async def delete(self, txn_key):
        """

        :param txn_key:
        :return:
        """
        assert type(txn_key) == tuple and len(txn_key) == 2

        txn, key = txn_key

        _key = struct.pack('>H', self._slot) + self._serialize_key(key)

        if self._indexes:
            value = await self.__getitem__(txn_key)

        txn.delete(_key)

        if self._indexes:
            for index in self._indexes:
                _key = struct.pack('>H', index.pmap._slot) + index.pmap._serialize_key(index.fkey(value))
                txn.delete(_key)

    def __len__(self):
        raise Exception('not implemented')

    def __iter__(self):
        raise Exception('not implemented')

    async def watch(self, txn, on_watch, from_key=None, to_key=None):
        """

        :param txn:
        :param on_watch:
        :param from_key:
        :param to_key:
        :return:
        """
        assert callable(on_watch)

        if from_key:
            from_key = self._serialize_key(from_key)
        else:
            from_key = struct.pack('>H', self._slot)

        if to_key:
            to_key = self._serialize_key(to_key)
        else:
            to_key = struct.pack('>H', self._slot + 1)

        watching = await txn.watch(on_watch, from_key=from_key, to_key=to_key, keys_only=False)

        return watching

    async def select(self, txn, from_key=None, to_key=None, return_keys=False, return_values=True):
        """

        :param txn:
        :param from_key:
        :param to_key:
        :param return_keys:
        :param return_values:
        :return:
        """
        assert return_keys or return_values

        if from_key:
            from_key = self._serialize_key(from_key)
        else:
            from_key = struct.pack('>H', self._slot)

        if to_key:
            to_key = self._serialize_key(to_key)
        else:
            to_key = struct.pack('>H', self._slot + 1)

        res_keys, res_values = None, None
        result = await txn.get(from_key, range_end=to_key, keys_only=not return_values)

        if result:
            if return_keys:
                res_keys = []

            if return_values:
                res_values = []

            for kv in result:
                if return_keys:
                    data = kv.key[2:]
                    obj = self._deserialize_key(data)
                    res_keys.append(obj)

                if return_values:
                    data = kv.value
                    if self._decompress:
                        data = self._decompress(data)
                    obj = self._deserialize_value(data)
                    res_values.append(obj)

        if return_keys and return_values:
            return res_keys, res_values
        elif return_keys:
            return res_keys
        elif return_values:
            return res_values
        else:
            raise Exception('logic error')

    async def count(self, txn, prefix=None):
        """

        :param txn:
        :param prefix:
        :return:
        """
        from_key = struct.pack('>H', self._slot)
        if prefix:
            from_key += self._serialize_key(prefix)
            to_key = ((int.from_bytes(from_key, byteorder='big') + 1).to_bytes(
                len(from_key), byteorder='big'))
        else:
            to_key = struct.pack('>H', self._slot + 1)

        result = await txn.get(from_key, range_end=to_key, count_only=True)
        return result

    def truncate(self, txn, rebuild_indexes=True):
        """

        :param txn:
        :param rebuild_indexes:
        :return:
        """
        key_from = struct.pack('>H', self._slot)
        key_to = struct.pack('>H', self._slot + 1)
        cursor = txn._txn.cursor()
        cnt = 0
        if cursor.set_range(key_from):
            key = cursor.key()
            while key < key_to:
                if not cursor.delete(dupdata=True):
                    break
                cnt += 1
                if txn._stats:
                    txn._stats.dels += 1
        if rebuild_indexes:
            deleted, _ = self.rebuild_indexes(txn)
            cnt += deleted
        return cnt

    def rebuild_indexes(self, txn):
        """

        :param txn:
        :return:
        """
        total_deleted = 0
        total_inserted = 0
        for index in self._indexes:
            deleted, inserted = index.rebuild(txn, index)
            total_deleted += deleted
            total_inserted += inserted
        return total_deleted, total_inserted

    def rebuild_index(self, txn, index):
        """

        :param txn:
        :param index:
        :return:
        """
        if index in self._indexes:

            deleted = index.pmap.truncate(txn)

            key_from = struct.pack('>H', self._slot)
            key_to = struct.pack('>H', self._slot + 1)
            cursor = txn._txn.cursor()
            inserted = 0
            if cursor.set_range(key_from):
                while cursor.key() < key_to:
                    data = cursor.value()
                    if data:
                        value = self._deserialize_value(data)

                        _key = struct.pack('>H', index.pmap._slot) + index.pmap._serialize_key(
                            index.fkey(value))
                        _data = index.pmap._serialize_value(value.oid)

                        txn.put(_key, _data)
                        inserted += 1
                    if not cursor.next():
                        break
            return deleted, inserted
        else:
            raise IndexError('no such index attached')


#
# Key: UUID -> Value: String, OID, UUID, JSON, CBOR, Pickle, FlatBuffers
#


class MapSlotUuidUuid(_types._SlotUuidKeysMixin, _types._UuidValuesMixin, PersistentMap):
    """
    Persistent map with (slot, UUID) and UUID values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapUuidString(_types._UuidKeysMixin, _types._StringValuesMixin, PersistentMap):
    """
    Persistent map with UUID (16 bytes) keys and string (utf8) values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapUuidOid(_types._UuidKeysMixin, _types._OidValuesMixin, PersistentMap):
    """
    Persistent map with UUID (16 bytes) keys and OID (uint64) values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapUuidUuid(_types._UuidKeysMixin, _types._UuidValuesMixin, PersistentMap):
    """
    Persistent map with UUID (16 bytes) keys and UUID (16 bytes) values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapUuidUuidSet(_types._UuidKeysMixin, _types._UuidSetValuesMixin, PersistentMap):
    """
    Persistent map with UUID keys and UUID set values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapUuidStringUuid(_types._UuidStringKeysMixin, _types._UuidValuesMixin, PersistentMap):
    """
    Persistent map with (UUID, string) keys and UUID values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapUuidUuidUuid(_types._UuidUuidKeysMixin, _types._UuidValuesMixin, PersistentMap):
    """
    Persistent map with (UUID, UUID) keys and UUID values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapUuidJson(_types._UuidKeysMixin, _types._JsonValuesMixin, PersistentMap):
    """
    Persistent map with UUID (16 bytes) keys and JSON values.
    """

    def __init__(self, slot=None, compress=None, marshal=None, unmarshal=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)
        _types._JsonValuesMixin.__init__(self, marshal=marshal, unmarshal=unmarshal)


class MapUuidCbor(_types._UuidKeysMixin, _types._CborValuesMixin, PersistentMap):
    """
    Persistent map with UUID (16 bytes) keys and CBOR values.
    """

    def __init__(self, slot=None, compress=None, marshal=None, unmarshal=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)
        _types._CborValuesMixin.__init__(self, marshal=marshal, unmarshal=unmarshal)


class MapUuidUuidCbor(_types._UuidUuidKeysMixin, _types._CborValuesMixin, PersistentMap):
    """
    Persistent map with (UUID, UUID) keys and CBOR values.
    """

    def __init__(self, slot=None, compress=None, marshal=None, unmarshal=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)
        _types._CborValuesMixin.__init__(self, marshal=marshal, unmarshal=unmarshal)


class MapUuidPickle(_types._UuidKeysMixin, _types._PickleValuesMixin, PersistentMap):
    """
    Persistent map with UUID (16 bytes) keys and Python Pickle values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapUuidFlatBuffers(_types._UuidKeysMixin, _types._FlatBuffersValuesMixin, PersistentMap):
    """
    Persistent map with UUID (16 bytes) keys and FlatBuffers values.
    """

    def __init__(self, slot=None, compress=None, build=None, cast=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)
        _types._FlatBuffersValuesMixin.__init__(self, build=build, cast=cast)


#
# Key: String -> Value: String, OID, UUID, JSON, CBOR, Pickle, FlatBuffers
#


class MapStringString(_types._StringKeysMixin, _types._StringValuesMixin, PersistentMap):
    """
    Persistent map with string (utf8) keys and string (utf8) values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapStringOid(_types._StringKeysMixin, _types._OidValuesMixin, PersistentMap):
    """
    Persistent map with string (utf8) keys and OID (uint64) values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapStringUuid(_types._StringKeysMixin, _types._UuidValuesMixin, PersistentMap):
    """
    Persistent map with string (utf8) keys and UUID (16 bytes) values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapStringJson(_types._StringKeysMixin, _types._JsonValuesMixin, PersistentMap):
    """
    Persistent map with string (utf8) keys and JSON values.
    """

    def __init__(self, slot=None, compress=None, marshal=None, unmarshal=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)
        _types._JsonValuesMixin.__init__(self, marshal=marshal, unmarshal=unmarshal)


class MapStringCbor(_types._StringKeysMixin, _types._CborValuesMixin, PersistentMap):
    """
    Persistent map with string (utf8) keys and CBOR values.
    """

    def __init__(self, slot=None, compress=None, marshal=None, unmarshal=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)
        _types._CborValuesMixin.__init__(self, marshal=marshal, unmarshal=unmarshal)


class MapStringPickle(_types._StringKeysMixin, _types._PickleValuesMixin, PersistentMap):
    """
    Persistent map with string (utf8) keys and Python pickle values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapStringFlatBuffers(_types._StringKeysMixin, _types._FlatBuffersValuesMixin, PersistentMap):
    """
    Persistent map with string (utf8) keys and FlatBuffers values.
    """

    def __init__(self, slot=None, compress=None, build=None, cast=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)
        _types._FlatBuffersValuesMixin.__init__(self, build=build, cast=cast)


#
# Key: OID -> Value: String, OID, UUID, JSON, CBOR, Pickle, FlatBuffers
#


class MapOidString(_types._OidKeysMixin, _types._StringValuesMixin, PersistentMap):
    """
    Persistent map with OID (uint64) keys and string (utf8) values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapOidOid(_types._OidKeysMixin, _types._OidValuesMixin, PersistentMap):
    """
    Persistent map with OID (uint64) keys and OID (uint64) values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapOidUuid(_types._OidKeysMixin, _types._UuidValuesMixin, PersistentMap):
    """
    Persistent map with OID (uint64) keys and UUID (16 bytes) values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapOidJson(_types._OidKeysMixin, _types._JsonValuesMixin, PersistentMap):
    """
    Persistent map with OID (uint64) keys and JSON values.
    """

    def __init__(self, slot=None, compress=None, marshal=None, unmarshal=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)
        _types._JsonValuesMixin.__init__(self, marshal=marshal, unmarshal=unmarshal)


class MapOidCbor(_types._OidKeysMixin, _types._CborValuesMixin, PersistentMap):
    """
    Persistent map with OID (uint64) keys and CBOR values.
    """

    def __init__(self, slot=None, compress=None, marshal=None, unmarshal=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)
        _types._CborValuesMixin.__init__(self, marshal=marshal, unmarshal=unmarshal)


class MapOidPickle(_types._OidKeysMixin, _types._PickleValuesMixin, PersistentMap):
    """
    Persistent map with OID (uint64) keys and Python pickle values.
    """

    def __init__(self, slot=None, compress=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)


class MapOidFlatBuffers(_types._OidKeysMixin, _types._FlatBuffersValuesMixin, PersistentMap):
    """
    Persistent map with OID (uint64) keys and FlatBuffers values.
    """

    def __init__(self, slot=None, compress=None, build=None, cast=None):
        PersistentMap.__init__(self, slot=slot, compress=compress)
        _types._FlatBuffersValuesMixin.__init__(self, build=build, cast=cast)
