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

__all__ = (
    'Value',
    'Header',
    'Status',
    'Deleted',
)


class Value(object):
    """
    An etcd value (stored for a key).
    """

    def __init__(self, value, version=None, create_revision=None, mod_revision=None):
        """

        :param value: The actual value.
        :type value: bytes
        :param version:
        :type version:
        :param create_revision:
        :type create_revision:
        :param mod_revision:
        :type mod_revision
        """
        self.value = value
        self.version = version
        self.create_revision = create_revision
        self.mod_revision = mod_revision

    def __str__(self):
        return 'Value({}, version={}, create_revision={}, mod_revision{})'.format(self.value, self.version, self.create_revision, self.mod_revision)


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
        raft_term = int(obj['raft_term']) if 'raft_term' in obj else None
        revision = int(obj['revision']) if 'revision' in obj else None
        cluster_id = int(obj['cluster_id']) if 'cluster_id' in obj else None
        member_id = int(obj['member_id']) if 'member_id' in obj else None
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
        version = obj['version'] if 'version' in obj else None
        dbSize = int(obj['dbSize']) if 'dbSize' in obj else None
        leader = int(obj['leader']) if 'leader' in obj else None
        header = Header.parse(obj['header']) if 'header' in obj else None
        raftTerm = int(obj['raftTerm']) if 'raftTerm' in obj else None
        raftIndex = int(obj['raftIndex']) if 'raftIndex' in obj else None
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
    """
    def __init__(self, deleted, header):
        self.deleted = deleted
        self.header = header

    @staticmethod
    def parse(obj):
        deleted = int(obj['deleted']) if 'deleted' in obj else None
        header = Header.parse(obj['header']) if 'header' in obj else None
        return Deleted(deleted, header)

    def __str__(self):
        return u'Deleted(deleted={}, header={})'.format(self.deleted, self.header)
