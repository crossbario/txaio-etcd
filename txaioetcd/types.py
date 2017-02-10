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

import six


__all__ = (
    'KeySet',
    'KeyValue',
    'Header',
    'Status',
    'Deleted',
    'Revision',
)


def _maybe_text(data):
    try:
        return u'{}'.format(data)
    except:
        return binascii.b2a_hex(data)


class KeySet(object):
    """
    Represents a set of etcd keys. Either a single key, a key range or
    all keys with a given prefix.
    """

    SINGLE = u'single'
    """
    Key set is a single key - hence the set is degenarate.
    """

    RANGE = u'range'
    """
    Key set is a range of keys.
    """

    PREFIX = u'prefix'
    """
    Key set is determined by prefix (all keys having the same given prefix).
    """

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
            self.type = self.PREFIX
        elif range_end:
            self.type = self.RANGE
        else:
            self.type = self.SINGLE


class KeyValue(object):
    """
    An etcd key-value.

    .. code-block:: json

        {
            'key': 'bXlrZXkz',
            'value': 'd29hOyk=',
            'version': '1',
            'create_revision': '357',
            'mod_revision': '357'
        }
    """

    def __init__(self, key, value, version=None, create_revision=None, mod_revision=None):
        """

        :param key: The key.
        :type key: bytes
        :param value: The value.
        :type value: bytes
        :param version:
        :type version:
        :param create_revision:
        :type create_revision:
        :param mod_revision:
        :type mod_revision
        """
        self.key = key
        self.value = value
        self.version = version
        self.create_revision = create_revision
        self.mod_revision = mod_revision

    @staticmethod
    def parse(obj):
        key = binascii.a2b_base64(obj[u'key']) if u'key' in obj else None
        value = binascii.a2b_base64(obj[u'value']) if u'value' in obj else None
        version = int(obj[u'version']) if u'version' in obj else None
        create_revision = int(obj[u'create_revision']) if u'create_revision' in obj else None
        mod_revision = int(obj[u'mod_revision']) if u'mod_revision' in obj else None
        return KeyValue(key, value, version, create_revision, mod_revision)

    def __str__(self):
        return u'KeyValue(key={}, value={}, version={}, create_revision={}, mod_revision{})'.format(_maybe_text(self.key), _maybe_text(self.value), self.version, self.create_revision, self.mod_revision)


class Header(object):
    """
    An etcd header.

    .. code-block:: json

        u'header':
        {
            u'raft_term': u'2',
            u'revision': u'285',
            u'cluster_id': u'243774308834426361',
            u'member_id': u'17323375927490080838'
        }
    """
    def __init__(self, raft_term, revision, cluster_id, member_id):
        self.raft_term = raft_term
        self.revision = revision
        self.cluster_id = cluster_id
        self.member_id = member_id

    @staticmethod
    def parse(obj):
        raft_term = int(obj[u'raft_term']) if u'raft_term' in obj else None
        revision = int(obj[u'revision']) if u'revision' in obj else None
        cluster_id = int(obj[u'cluster_id']) if u'cluster_id' in obj else None
        member_id = int(obj[u'member_id']) if u'member_id' in obj else None
        return Header(raft_term, revision, cluster_id, member_id)

    def __str__(self):
        return u'Header(raft_term={}, revision={}, cluster_id={}, member_id={})'.format(self.raft_term, self.revision, self.cluster_id, self.member_id)


class Status(object):
    """
    etcd status.

    .. code-block:: json

        {
            u'raftTerm': u'2',
            u'header':
            {
                u'raft_term': u'2',
                u'revision': u'285',
                u'cluster_id': u'243774308834426361',
                u'member_id': u'17323375927490080838'
            },
            u'version': u'3.1.0',
            u'raftIndex': u'288',
            u'dbSize': u'57344',
            u'leader': u'17323375927490080838'
        }
    """
    def __init__(self, version, dbSize, leader, header, raftTerm, raftIndex):
        self.version = version
        self.dbSize = dbSize
        self.leader = leader
        self.header = header
        self.raftTerm = raftTerm
        self.raftIndex = raftIndex

    @staticmethod
    def parse(obj):
        version = obj[u'version'] if u'version' in obj else None
        dbSize = int(obj[u'dbSize']) if u'dbSize' in obj else None
        leader = int(obj[u'leader']) if u'leader' in obj else None
        header = Header.parse(obj[u'header']) if u'header' in obj else None
        raftTerm = int(obj[u'raftTerm']) if u'raftTerm' in obj else None
        raftIndex = int(obj[u'raftIndex']) if u'raftIndex' in obj else None
        return Status(version, dbSize, leader, header, raftTerm, raftIndex)

    def __str__(self):
        return u'Status(version={}, dbSize={}, leader={}, header={}, raftTerm={}, raftIndex={})'.format(self.version, self.dbSize, self.leader, self.header, self.raftTerm, self.raftIndex)


class Deleted(object):
    """
    Info for key deleted from etcd.

    .. code-block:: json

        {
            u'deleted': u'1',
            u'header':
            {
                u'raft_term': u'2',
                u'revision': u'334',
                u'cluster_id': u'243774308834426361',
                u'member_id': u'17323375927490080838'
            }
        }

    or

    .. code-block:: json

        {
            'deleted': '1',
            'header':
            {
                'cluster_id': '15378991040070777582',
                'member_id': '4884146582048902091',
                'raft_term': '2',
                'revision': '362'
            },
            'prev_kvs': [
                {
                    'create_revision': '357',
                    'key': 'bXlrZXkz',
                    'mod_revision': '357',
                    'value': 'd29hOyk=',
                    'version': '1'
                }
            ]
        }
    """
    def __init__(self, deleted, header, previous=None):
        self.deleted = deleted
        self.header = header
        self.previous = previous

    @staticmethod
    def parse(obj):
        deleted = int(obj[u'deleted']) if u'deleted' in obj else None
        header = Header.parse(obj[u'header']) if u'header' in obj else None
        if u'prev_kvs' in obj:
            previous = []
            for kv in obj[u'prev_kvs']:
                previous.append(KeyValue.parse(kv))
        else:
            previous = None
        return Deleted(deleted, header, previous)

    def __str__(self):
        previous_str = u'[' + u', '.join(str(value) for value in self.previous) + u']' if self.previous else None
        return u'Deleted(deleted={}, header={}, previous={})'.format(self.deleted, self.header, previous_str)


class Revision(object):
    """
    Info from etcd for setting a key.

    .. code-block:: json

        {
            u'header':
            {
                u'raft_term': u'2',
                u'revision': u'100',
                u'cluster_id': u'243774308834426361',
                u'member_id': u'17323375927490080838'
            }
        }

    or

    .. code-block:: json

        {
            u'header':
            {
                u'raft_term': u'2',
                u'revision': u'102',
                u'cluster_id': u'243774308834426361',
                u'member_id': u'17323375927490080838'
            },
            u'prev_kv':
            {
                u'mod_revision': u'101',
                u'value': u'YmFy',
                u'create_revision': u'98',
                u'version': u'4'
                ,u'key': u'Zm9v'
            }
        }

    """
    def __init__(self, header, previous=None):
        self.header = header
        self.previous = previous

    @staticmethod
    def parse(obj):
        header = Header.parse(obj[u'header']) if u'header' in obj else None
        if u'prev_kv' in obj:
            previous = KeyValue.parse(obj[u'prev_kv'])
        else:
            previous = None
        return Revision(header, previous)

    def __str__(self):
        return u'Revision(header={}, previous={})'.format(self.header, self.previous)
