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

import binascii
import base64

import six


__all__ = (
    'KeySet',
    'KeyValue',
    'Header',
    'Status',
    'Deleted',
    'Revision',
    'Comp',
    'CompValue',
    'CompVersion',
    'CompCreated',
    'CompModified',
    'Op',
    'OpGet',
    'OpSet',
    'OpDel',
    'Transaction',
    'Error',
    'Failed',
    'Success',
    'Expired',
    'Range'
)


def _increment_last_byte(byte_string):
    """
    Increment a byte string by 1 - this is used for etcd prefix gets/watches.

    FIXME: This function is doing it wrong when the last octet equals 0xFF.
    FIXME: This function is doing it wrong when the byte_string is of length 0
    """
    s = bytearray(byte_string)
    s[-1] = s[-1] + 1
    return bytes(s)


def _maybe_text(data):
    try:
        return u'{}'.format(data)
    except:
        return binascii.b2a_hex(data).decode()


class KeySet(object):
    """
    Represents a set of etcd keys. Either a single key, a key range or
    all keys with a given prefix.
    """

    # Key set is a single key - hence the set is degenarate.
    _SINGLE = u'single'

    # Key set is a range of keys.
    _RANGE = u'range'

    # Key set is determined by prefix (all keys having the same given prefix).
    _PREFIX = u'prefix'

    def __init__(self, key, range_end=None, prefix=None):
        """

        :param key: The key range start or the key prefix.
        :type key: bytes

        :param range_end: The key range end
        :type range_end: bytes or None

        :param prefix: If enabled, the key set is determined by prefix.
        :type prefix: bool or None
        """
        if type(key) != six.binary_type:
            raise TypeError('key must be bytes type, not {}'.format(type(key)))
        if range_end is not None and type(range_end) != six.binary_type:
            raise TypeError('range_end must be bytes type, not {}'.format(type(range_end)))
        if prefix is not None and type(prefix) != bool:
            raise TypeError('prefix must be bool type, not {}'.format(type(prefix)))
        if prefix and range_end:
            raise TypeError('either range_end or prefix can be set, but not both')

        self.key = key
        self.range_end = range_end
        self.prefix = prefix

        if prefix:
            self.type = KeySet._PREFIX
        elif range_end:
            self.type = KeySet._RANGE
        else:
            self.type = KeySet._SINGLE

    def _marshal(self):
        obj = {
            u'key': base64.b64encode(self.key).decode()
        }

        if self.type == KeySet._SINGLE:
            range_end = None
        elif self.type == KeySet._PREFIX:
            range_end = _increment_last_byte(self.key)
        elif self.type == KeySet._RANGE:
            range_end = self.range_end
        else:
            raise Exception('logic error')

        if range_end:
            obj[u'range_end'] = base64.b64encode(range_end).decode()

        return obj

    def __str__(self):
        return u'KeySet(type={}, key={}, range_end={}, prefix={})'.format(self.type, _maybe_text(self.key), _maybe_text(self.range_end), self.prefix)


class KeyValue(object):
    """
    An etcd key-value.

    :ivar key: The key.
    :vartype key: bytes

    :ivar value: The value.
    :vartype value: bytes

    :ivar version: Version of the key. A deletion resets the version to zero and any
        modification of the key increases its version.
    :vartype version: int

    :ivar create_revision: Revision of last creation on this key.
    :vartype create_revision: int

    :ivar mod_revision: Revision of last modification on this key.
    :vartype mod_revision: int
    """

    def __init__(self, key, value, version=None, create_revision=None, mod_revision=None):
        self.key = key
        self.value = value
        self.version = version
        self.create_revision = create_revision
        self.mod_revision = mod_revision

    @staticmethod
    def _parse(obj):
        # {
        #     'key': 'bXlrZXkz',
        #     'value': 'd29hOyk=',
        #     'version': '1',
        #     'create_revision': '357',
        #     'mod_revision': '357'
        # }

        key = base64.b64decode(obj[u'key']) if u'key' in obj else None
        value = base64.b64decode(obj[u'value']) if u'value' in obj else None
        version = int(obj[u'version']) if u'version' in obj else None
        create_revision = int(obj[u'create_revision']) if u'create_revision' in obj else None
        mod_revision = int(obj[u'mod_revision']) if u'mod_revision' in obj else None
        return KeyValue(key, value, version, create_revision, mod_revision)

    def __str__(self):
        return u'KeyValue(key={}, value={}, version={}, create_revision={}, mod_revision={})'.format(_maybe_text(self.key), _maybe_text(self.value), self.version, self.create_revision, self.mod_revision)


class Header(object):
    """
    An etcd response header.

    :ivar raft_term: Raft term when the request was applied.
    :vartype raft_term: int

    :ivar revision: Key-value store revision when the request was applied.
    :vartype revision: int

    :ivar cluster_id: ID of the cluster which sent the response.
    :vartype cluster_id: int

    :ivar member_id: ID of the cluster which sent the response.
    :vartype member_id: int

    """
    def __init__(self, raft_term, revision, cluster_id, member_id):
        self.raft_term = raft_term
        self.revision = revision
        self.cluster_id = cluster_id
        self.member_id = member_id

    @staticmethod
    def _parse(obj):
        # u'header':
        # {
        #     u'raft_term': u'2',
        #     u'revision': u'285',
        #     u'cluster_id': u'243774308834426361',
        #     u'member_id': u'17323375927490080838'
        # }
        raft_term = int(obj[u'raft_term']) if u'raft_term' in obj else None
        revision = int(obj[u'revision']) if u'revision' in obj else None
        cluster_id = int(obj[u'cluster_id']) if u'cluster_id' in obj else None
        member_id = int(obj[u'member_id']) if u'member_id' in obj else None
        return Header(raft_term, revision, cluster_id, member_id)

    def __str__(self):
        return u'Header(raft_term={}, revision={}, cluster_id={}, member_id={})'.format(self.raft_term, self.revision, self.cluster_id, self.member_id)


class Status(object):
    """
    etcd cluster status.

    :ivar version: Cluster protocol version used by the responding member.
    :vartype version: str

    :ivar db_size: Size of the backend database, in bytes, of the responding member.
    :vartype db_size: int

    :ivar leader: Member ID which the responding member believes is the current leader.
    :vartype leader: int

    :ivar header: Response header.
    :vartype header: instance of :class:`txaioetcd.Header`

    :ivar raft_term: Current raft term of the responding member.
    :vartype raft_term: int

    :ivar raft_index: Current raft index of the responding member.
    :vartype raft_index: int
    """
    def __init__(self, version, db_size, leader, header, raft_term, raft_index):
        self.version = version
        self.db_size = db_size
        self.leader = leader
        self.header = header
        self.raft_term = raft_term
        self.raft_index = raft_index

    @staticmethod
    def _parse(obj):
        # {
        #     u'raftTerm': u'2',
        #     u'header':
        #     {
        #         u'raft_term': u'2',
        #         u'revision': u'285',
        #         u'cluster_id': u'243774308834426361',
        #         u'member_id': u'17323375927490080838'
        #     },
        #     u'version': u'3.1.0',
        #     u'raftIndex': u'288',
        #     u'dbSize': u'57344',
        #     u'leader': u'17323375927490080838'
        # }
        version = obj[u'version'] if u'version' in obj else None
        db_size = int(obj[u'dbSize']) if u'dbSize' in obj else None
        leader = int(obj[u'leader']) if u'leader' in obj else None
        header = Header._parse(obj[u'header']) if u'header' in obj else None
        raft_term = int(obj[u'raftTerm']) if u'raftTerm' in obj else None
        raft_index = int(obj[u'raftIndex']) if u'raftIndex' in obj else None
        return Status(version, db_size, leader, header, raft_term, raft_index)

    def __str__(self):
        return u'Status(version={}, db_size={}, leader={}, header={}, raft_term={}, raft_index={})'.format(self.version, self.db_size, self.leader, self.header, self.raft_term, self.raft_index)


class Deleted(object):
    """
    Info for key deleted from etcd.

    :ivar deleted: The number of deleted KVs.
    :vartype deleted: int

    :ivar header: Response header.
    :vartype header: instance of :class:`txaioetcd.Header`

    :ivar previous: Previous Key-Value pairs (if requested).
    :vartype previous: list or None
    """

    def __init__(self, deleted, header, previous=None):
        self.deleted = deleted or 0
        self.header = header
        self.previous = previous or []

    @staticmethod
    def _parse(obj):

        # {
        #     u'deleted': u'1',
        #     u'header':
        #     {
        #         u'raft_term': u'2',
        #         u'revision': u'334',
        #         u'cluster_id': u'243774308834426361',
        #         u'member_id': u'17323375927490080838'
        #     }
        # }
        #
        # OR (previous KVs returned)
        #
        # {
        #     'deleted': '1',
        #     'header':
        #     {
        #         'cluster_id': '15378991040070777582',
        #         'member_id': '4884146582048902091',
        #         'raft_term': '2',
        #         'revision': '362'
        #     },
        #     'prev_kvs': [
        #         {
        #             'create_revision': '357',
        #             'key': 'bXlrZXkz',
        #             'mod_revision': '357',
        #             'value': 'd29hOyk=',
        #             'version': '1'
        #         }
        #     ]
        # }

        deleted = int(obj[u'deleted']) if u'deleted' in obj else None
        header = Header._parse(obj[u'header']) if u'header' in obj else None
        if u'prev_kvs' in obj:
            previous = []
            for kv in obj[u'prev_kvs']:
                previous.append(KeyValue._parse(kv))
        else:
            previous = None
        return Deleted(deleted, header, previous)

    def __str__(self):
        previous_str = u'[' + u', '.join(str(value) for value in self.previous) + u']' if self.previous else None
        return u'Deleted(deleted={}, header={}, previous={})'.format(self.deleted, self.header, previous_str)


class Revision(object):
    """
    Info from etcd for setting a key.

    :ivar header: Response header.
    :vartype header: instance of :class:`txaioetcd.Header`

    :ivar previous: Previous KVs (if requested).
    :vartype previous: list or None
    """
    def __init__(self, header, previous=None):
        """

        :param header:
        :type header: instance of Header

        :param previous:
        :type previous: list of instance of KeyValue
        """
        self.header = header
        self.previous = previous

    @staticmethod
    def _parse(obj):

        # {
        #     u'header':
        #     {
        #         u'raft_term': u'2',
        #         u'revision': u'100',
        #         u'cluster_id': u'243774308834426361',
        #         u'member_id': u'17323375927490080838'
        #     }
        # }
        #
        # OR
        #
        # {
        #     u'header':
        #     {
        #         u'raft_term': u'2',
        #         u'revision': u'102',
        #         u'cluster_id': u'243774308834426361',
        #         u'member_id': u'17323375927490080838'
        #     },
        #     u'prev_kv':
        #     {
        #         u'mod_revision': u'101',
        #         u'value': u'YmFy',
        #         u'create_revision': u'98',
        #         u'version': u'4'
        #         ,u'key': u'Zm9v'
        #     }
        # }

        header = Header._parse(obj[u'header']) if u'header' in obj else None
        if u'prev_kv' in obj:
            previous = KeyValue._parse(obj[u'prev_kv'])
        else:
            previous = None
        return Revision(header, previous)

    def __str__(self):
        return u'Revision(header={}, previous={})'.format(self.header, self.previous)


class Comp(object):
    """
    Base class for representing comparisons against a KV item.

    :ivar key: The subject key for the comparison operation.
    :vartype key: bytes

    :ivar compare: The comparison operator to apply.
    :vartype compare: str
    """

    OPERATORS = {
        u'==': u'EQUAL',
        u'!=': u'NOT_EQUAL',
        u'>': u'GREATER',
        u'<': u'LESS',
    }
    """
    etcd API: CompareCompareResult
    """

    def __init__(self, key, compare):
        if type(key) != six.binary_type:
            raise TypeError('key must be bytes type, not {}'.format(type(key)))

        if compare not in Comp.OPERATORS:
            raise TypeError('compare must be one of {}, not "{}"'.format(Comp.OPERATORS, compare))

        self.key = key
        self.compare = compare

    def _marshal(self):
        obj = {
            u'key': base64.b64encode(self.key).decode(),
            u'result': Comp.OPERATORS[self.compare]
        }
        return obj

    def __str__(self):
        return u'Comp(key={}, compare="{}")'.format(_maybe_text(self.key), self.compare)


class CompValue(Comp):
    """
    Represents a comparison against a KV value.

    :ivar key: The subject key for the comparison operation.
    :vartype key: bytes

    :ivar compare: The comparison operator to apply.
    :vartype compare: str

    :ivar value: The value to compare to.
    :vartype value: bytes
    """

    def __init__(self, key, compare, value):
        Comp.__init__(self, key, compare)

        if type(value) != six.binary_type:
            raise TypeError('value must be bytes type, not {}'.format(type(value)))

        self.value = value

    def _marshal(self):
        obj = Comp._marshal(self)
        obj[u'target'] = u'VALUE'  # CompareCompareTarget
        obj[u'value'] = base64.b64encode(self.value).decode()
        return obj

    def __str__(self):
        return u'CompValue(key={}, compare="{}", value={})'.format(_maybe_text(self.key), self.compare, _maybe_text(self.value))


class CompVersion(Comp):
    """
    Represents a comparison against a KV version.

    :ivar key: The subject key for the comparison operation.
    :vartype key: bytes

    :ivar compare: The comparison operator to apply.
    :vartype compare: str

    :ivar version: The value to compare to.
    :vartype version: int
    """

    def __init__(self, key, compare, version):
        Comp.__init__(self, key, compare)

        if type(version) not in six.integer_types:
            raise TypeError('version must be an integer type, not {}'.format(type(version)))

        self.version = version

    def _marshal(self):
        obj = Comp._marshal(self)
        obj[u'target'] = u'VERSION'  # CompareCompareTarget
        obj[u'version'] = self.version
        return obj

    def __str__(self):
        return u'CompVersion(key={}, compare="{}", version={})'.format(_maybe_text(self.key), self.compare, self.version)


class CompCreated(Comp):
    """
    Represents a comparison against a KV create_revision.

    :ivar key: The subject key for the comparison operation.
    :vartype key: bytes

    :ivar compare: The comparison operator to apply.
    :vartype compare: str

    :ivar create_revision: The value to compare to.
    :vartype create_revision: int
    """

    def __init__(self, key, compare, create_revision):
        Comp.__init__(self, key, compare)

        if type(create_revision) not in six.integer_types:
            raise TypeError('create_revision must be an integer type, not {}'.format(type(create_revision)))

        self.create_revision = create_revision

    def _marshal(self):
        obj = Comp._marshal(self)
        obj[u'target'] = u'CREATE'  # CompareCompareTarget
        obj[u'create_revision'] = self.create_revision
        return obj

    def __str__(self):
        return u'CompCreated(key={}, compare="{}", create_revision={})'.format(_maybe_text(self.key), self.compare, self.create_revision)


class CompModified(Comp):
    """
    Represents a comparison against a KV mod_revision.

    :ivar key: The subject key for the comparison operation.
    :vartype key: bytes

    :ivar compare: The comparison operator to apply.
    :vartype compare: str

    :ivar mod_revision: The value to compare to.
    :vartype mod_revision: int
    """

    def __init__(self, key, compare, mod_revision):
        Comp.__init__(self, key, compare)

        if type(mod_revision) not in six.integer_types:
            raise TypeError('mod_revision must be an integer type, not {}'.format(type(mod_revision)))

        self.mod_revision = mod_revision

    def _marshal(self):
        obj = Comp._marshal(self)
        obj[u'target'] = u'MOD'  # CompareCompareTarget
        obj[u'mod_revision'] = self.mod_revision
        return obj

    def __str__(self):
        return u'CompModified(key={}, compare="{}", mod_revision={})'.format(_maybe_text(self.key), self.compare, self.mod_revision)


class Op(object):
    """
    Base class that represents a single operation within a transaction.
    """


class OpGet(Op):
    """
    Represents a get operation as part of a transaction.
    """

    SORT_TARGETS = (u'KEY', u'VERSION', u'CREATE', u'MOD', u'VALUE')
    """
    Permissible sort targets.
    """

    SORT_ORDERS = (u'NONE', u'ASCEND', u'DESCEND')
    """
    Permissible sort orders.
    """

    def __init__(self,
                 key,
                 count_only=None,
                 keys_only=None,
                 limit=None,
                 max_create_revision=None,
                 min_create_revision=None,
                 min_mod_revision=None,
                 revision=None,
                 serializable=None,
                 sort_order=None,
                 sort_target=None):
        """

        :param key: The key to get.
        :type key: bytes or :class:`txaioetcd.KeySet`

        :param count_only:
        :type count_only:

        :param keys_only:
        :type keys_only:

        :param limit:
        :type limit:

        :param max_create_revision:
        :type max_create_revision:

        :param min_create_revision:
        :type min_create_revision:

        :param min_mod_revision:
        :type min_mod_revision:

        :param revision:
        :type revision:

        :param serializable:
        :type serializable:

        :param sort_order:
        :type sort_order:

        :param sort_target:
        :type sort_target:
        """
        Op.__init__(self)

        if key is not None and type(key) != six.binary_type and not isinstance(key, KeySet):
            raise TypeError('key must be bytes or KeySet, not {}'.format(type(key)))

        if isinstance(key, KeySet):
            self.key = key
        else:
            self.key = KeySet(key)

        if count_only is not None and type(count_only) != bool:
            raise TypeError('count_only must be bool, not {}'.format(type(count_only)))

        if keys_only is not None and type(keys_only) != bool:
            raise TypeError('keys_only must be bool, not {}'.format(type(keys_only)))

        if limit is not None and type(limit) not in six.integer_types:
            raise TypeError('limit must be integer, not {}'.format(type(limit)))

        if max_create_revision is not None and type(max_create_revision) not in six.integer_types:
            raise TypeError('max_create_revision must be integer, not {}'.format(type(max_create_revision)))

        if min_create_revision is not None and type(min_create_revision) not in six.integer_types:
            raise TypeError('min_create_revision must be integer, not {}'.format(type(min_create_revision)))

        if min_mod_revision is not None and type(min_mod_revision) not in six.integer_types:
            raise TypeError('min_mod_revision must be integer, not {}'.format(type(min_mod_revision)))

        if revision is not None and type(revision) not in six.integer_types:
            raise TypeError('revision must be integer, not {}'.format(type(revision)))

        if serializable is not None and type(serializable) != bool:
            raise TypeError('serializable must be bool, not {}'.format(type(serializable)))

        if sort_target is not None and sort_target not in OpGet.SORT_TARGETS:
            raise TypeError('sort_target must be one of {}, not {}'.format(OpGet.SORT_TARGETS, sort_target))

        if sort_order is not None and sort_order not in OpGet.SORT_ORDERS:
            raise TypeError('sort_order must be one of {}, not {}'.format(OpGet.SORT_ORDERS, sort_order))

        self.count_only = count_only
        self.keys_only = keys_only
        self.limit = limit
        self.max_create_revision = max_create_revision
        self.min_create_revision = min_create_revision
        self.min_mod_revision = min_mod_revision
        self.revision = revision
        self.serializable = serializable
        self.sort_order = sort_order
        self.sort_target = sort_target

    def _marshal(self):
        obj = {
            u'request_range': self.key._marshal()
        }
        if self.count_only:
            obj[u'request_range'][u'count_only'] = True

        if self.keys_only:
            obj[u'request_range'][u'keys_only'] = True

        if self.limit:
            obj[u'request_range'][u'limit'] = self.limit

        if self.max_create_revision:
            obj[u'request_range'][u'max_create_revision'] = self.max_create_revision

        if self.min_create_revision:
            obj[u'request_range'][u'min_create_revision'] = self.min_create_revision

        if self.min_mod_revision:
            obj[u'request_range'][u'min_mod_revision'] = self.min_mod_revision

        if self.revision:
            obj[u'request_range'][u'revision'] = self.revision

        if self.serializable:
            obj[u'request_range'][u'serializable'] = True

        if self.sort_order:
            obj[u'request_range'][u'sort_order'] = self.sort_order

        if self.sort_target:
            obj[u'request_range'][u'sort_target'] = self.sort_target

        return obj

    def __str__(self):
        return u'OpGet(key={})'.format(self.key)


class OpSet(Op):
    """
    Represents a set operation as part of a transaction.
    """

    def __init__(self, key, value, lease=None, return_previous=None):
        """

        :param key: The key to set.
        :type key: bytes

        :param value: The value to set.
        :type value: bytes

        :param lease:
        :type lease: instance of :class:`txaioetcd.Lease`

        :param return_previous:
        :type return_previous: bool or None
        
        """
        Op.__init__(self)

        if type(key) != six.binary_type:
            raise TypeError('key must be bytes type, not {}'.format(type(key)))

        if type(value) != six.binary_type:
            raise TypeError('value must be bytes type, not {}'.format(type(value)))

        # import here to break circular dep between _type.py and _lease.py
        from txaioetcd._lease import Lease
        if lease is not None and not isinstance(lease, Lease):
            raise TypeError('lease must be a Lease object, not {}'.format(type(lease)))

        if return_previous is not None and type(return_previous) != bool:
            raise TypeError('return_previous must be bool, not {}'.format(type(return_previous)))

        self.key = key
        self.value = value
        self.lease = lease
        self.return_previous = return_previous

    def _marshal(self):
        obj = {
            u'request_put': {
                u'key': base64.b64encode(self.key).decode(),
                u'value': base64.b64encode(self.value).decode()
            }
        }

        if self.lease:
            obj[u'request_put'][u'lease'] = self.lease.lease_id
        if self.return_previous:
            obj[u'request_put'][u'prev_kv'] = True

        return obj

    def __str__(self):
        return u'OpSet(key={}, value={}, lease={}, return_previous={})'.format(_maybe_text(self.key), _maybe_text(self.value, self.lease, self.return_previous))


class OpDel(Op):
    """
    Represents a delete operation as part of a transaction.
    """

    def __init__(self, key, return_previous=None):
        """

        :param key: The key or key set to delete.
        :type key: bytes or :class:`txaioetcd.KeySet`

        :param return_previous: If enabled, return the deleted key-value pairs
        :type return_previous: bool or None
        """
        Op.__init__(self)

        if key is not None and type(key) != six.binary_type and not isinstance(key, KeySet):
            raise TypeError('key must be bytes or KeySet, not {}'.format(type(key)))

        if isinstance(key, KeySet):
            self.key = key
        else:
            self.key = KeySet(key)

        if return_previous is not None and type(return_previous) != bool:
            raise TypeError('return_previous must be bool, not {}'.format(type(return_previous)))

        self.return_previous = return_previous

    def _marshal(self):
        obj = {
            u'request_delete_range': self.key._marshal()
        }

        if self.return_previous:
            obj[u'request_delete_range'][u'prev_kv'] = True

        return obj

    def __str__(self):
        return u'OpDel(key={})'.format(self.key)


class Transaction(object):
    """
    An etcd transaction.
    """

    def __init__(self, compare=None, success=None, failure=None):
        """

        :param compare: The comparisons this transaction should depend on.
        :type compare: list of instances of :class:`txaioetcd.Comp` or None

        :param success: In case the transaction is successful, list of operations to perform.
        :type success: list of instances of :class:`txaioetcd.Op` or None

        :param failure: In case the transaction is unsuccessful, the list of operations to perform.
        :type failure: list of instances of :class:`txaioetcd.Op` or None
        """
        if compare is not None:
            if type(compare) != list:
                raise TypeError('compare must be a list, not {}'.format(type(compare)))
            else:
                for c in compare:
                    if not isinstance(c, Comp):
                        raise TypeError('compare must be a list of Comp elements, but encountered element of type {}'.format(type(c)))

        if success is not None:
            if type(success) != list:
                raise TypeError('success must be a list, not {}'.format(type(success)))
            else:
                for op in success:
                    if not isinstance(op, Op):
                        raise TypeError('success must be a list of Op elements, but encountered element of type {}'.format(type(op)))

        if failure is not None:
            if type(failure) != list:
                raise TypeError('failure must be a list, not {}'.format(type(failure)))
            else:
                for op in failure:
                    if not isinstance(op, Op):
                        raise TypeError('failure must be a list of Op elements, but encountered element of type {}'.format(type(op)))

        self.compare = compare
        self.success = success
        self.failure = failure

    def _marshal(self):
        obj = {}
        if self.compare:
            obj[u'compare'] = [o._marshal() for o in self.compare]
        if self.success:
            obj[u'success'] = [o._marshal() for o in self.success]
        if self.failure:
            obj[u'failure'] = [o._marshal() for o in self.failure]
        return obj

    def __str__(self):
        compare = u'[' + u', '.join(str(x) for x in self.compare) + u']' if self.compare else None
        success = u'[' + u', '.join(str(x) for x in self.success) + u']' if self.success else None
        failure = u'[' + u', '.join(str(x) for x in self.failure) + u']' if self.failure else None
        return u'Transaction(compare={}, success={}, failure={})'.format(compare, success, failure)


class Error(RuntimeError):
    """
    Error from etcd.

    :ivar code: The etcd error code.
    :vartype code: int

    :ivar message: The etcd error message.
    :vartype message: str or None
    """

    def __init__(self, code, message):
        self.code = code
        self.message = message

    @staticmethod
    def _parse(obj):
        # {
        #   'code': 3,
        #   'error': 'etcdserver: duplicate key given in txn request'
        # }
        code = int(obj[u'code']) if u'code' in obj else None
        message = obj.get(u'error', None)
        return Error(code, message)

    def __str__(self):
        return u'Error(code={}, message="{}")'.format(self.code, self.message)


class Failed(RuntimeError):

    def __init__(self, header, responses):
        self.header = header
        self.responses = responses

    def __str__(self):
        responses = u'[' + u', '.join(str(x) for x in self.responses) + u']' if self.responses is not None else None
        return u'Failed(header={}, responses={})'.format(self.header, responses)


class Success(object):
    """
    A transaction succeeded.

    :ivar header: Response header.
    :vartype header: instance of :class:`txaioetcd.Header`

    :ivar responses: The responses from the success section of the transaction.
    :vartype responses:
    """

    def __init__(self, header, responses):
        self.header = header
        self.responses = responses

    def __str__(self):
        responses = u'[' + u', '.join(str(x) for x in self.responses) + u']' if self.responses is not None else None
        return u'Success(header={}, responses={})'.format(self.header, responses)


class Expired(RuntimeError):
    """
    A lease has expired.
    """

    def __init__(self):
        RuntimeError.__init__(self, u'lease expired')


class Range(object):
    """
    A KV range request response.

    :ivar kvs: The key-value pairs.
    :vartype kvs: list of :class:`txaioetcd.KeyValue`

    :ivar header: Response header.
    :vartype header: instance of :class:`txaioetcd.Response`

    :ivar count: Number of KVs in result.
    :vartype count: int
    """

    def __init__(self, kvs, header, count):
        self.kvs = kvs
        self.header = header
        self.count = count

    @staticmethod
    def _parse(obj):
        count = obj.get(u'count', None)
        header = Header._parse(obj[u'header']) if u'header' in obj else None
        kvs = []
        for kv in obj.get(u'kvs', []):
            kvs.append(KeyValue._parse(kv))
        return Range(kvs, header, count)

    def __str__(self):
        kvs = u'[' + u', '.join(str(x) for x in self.kvs) + u']'
        return u'Range(kvs={}, header={}, count={})'.format(kvs, self.header, self.count)
