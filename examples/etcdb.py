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

import uuid
import datetime
import random
from typing import Optional, List, Dict

import six

import txaio
txaio.use_twisted()

from twisted.internet.task import react
from twisted.internet.defer import ensureDeferred, inlineCallbacks

import txaioetcd
import zlmdb


class User(object):
    oid: int
    name: str
    authid: str
    uuid: uuid.UUID
    email: str
    birthday: datetime.date
    is_friendly: bool
    tags: Optional[List[str]]
    ratings: Dict[str, float] = {}
    friends: List[int] = []
    referred_by: int = None

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if other.oid != self.oid:
            return False
        if other.name != self.name:
            return False
        if other.authid != self.authid:
            return False
        if other.uuid != self.uuid:
            return False
        if other.email != self.email:
            return False
        if other.birthday != self.birthday:
            return False
        if other.is_friendly != self.is_friendly:
            return False
        if (self.tags and not other.tags) or (not self.tags and other.tags):
            return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return '\n{}\n'.format(pformat(self.marshal()))

    def marshal(self):
        obj = {
            'oid': self.oid,
            'name': self.name,
            'authid': self.authid,
            'uuid': self.uuid.hex if self.uuid else None,
            'email': self.email,
            'birthday': {
                'year': self.birthday.year if self.birthday else None,
                'month': self.birthday.month if self.birthday else None,
                'day': self.birthday.day if self.birthday else None,
            },
            'is_friendly': self.is_friendly,
            'tags': self.tags,
            'ratings': self.ratings,
            'friends': self.friends,
            'referred_by': self.referred_by,
        }
        return obj

    @staticmethod
    def parse(obj):
        user = User()
        user.oid = obj.get('oid', None)
        user.name = obj.get('name', None)
        user.authid = obj.get('authid', None)
        if 'uuid' in obj:
            user.uuid = uuid.UUID(hex=obj['uuid'])
        user.email = obj.get('email', None)
        if 'birthday' in obj:
            b = obj['birthday']
            user.birthday = datetime.date(b.get('year', None), b.get('month', None), b.get('day', None))
        user.is_friendly = obj.get('is_friendly', None)
        user.tags = obj.get('tags', None)
        user.ratings = obj.get('ratings', {})
        user.friends = obj.get('friends', [])
        user.referred_by = obj.get('referred_by', None)
        return user

    @staticmethod
    def create_test_user(oid=None):
        user = User()
        if oid is not None:
            user.oid = oid
        else:
            user.oid = random.randint(0, 9007199254740992)
        user.name = 'Test {}'.format(user.oid)
        user.authid = 'test-{}'.format(user.oid)
        user.uuid = uuid.uuid4()
        user.email = '{}@example.com'.format(user.authid)
        user.birthday = datetime.date(1950, 12, 24)
        user.is_friendly = True
        user.tags = ['geek', 'sudoko', 'yellow']
        for j in range(10):
            user.ratings['test-rating-{}'.format(j)] = random.random()
        user.friends = [random.randint(0, 9007199254740992) for _ in range(10)]
        user.referred_by = random.randint(0, 9007199254740992)
        return user


class UsersSchema(zlmdb.Schema):

    users: zlmdb.MapUuidCbor
    idx_users_by_name: zlmdb.MapStringUuid
    idx_users_by_email: zlmdb.MapStringUuid

    def __init__(self):
        super(UsersSchema, self).__init__()

        self.users = zlmdb.MapUuidCbor(1, marshal=lambda user: user.marshal(), unmarshal=User.parse)

        self.idx_users_by_name = zlmdb.MapStringUuid(2)
        self.users.attach_index('idx1', lambda user: user.name, self.idx_users_by_name)

        self.idx_users_by_email = zlmdb.MapStringUuid(3)
        self.users.attach_index('idx2', lambda user: user.email, self.idx_users_by_email)


async def main(reactor):

    etcd = txaioetcd.Client(reactor)
    status = await etcd.status()
    revision = status.header.revision
    print('connected to etcd: revision', revision)

    schema = UsersSchema()
    users = schema.users
    idx1 = schema.idx_users_by_name
    print('using schema {}: users'.format(schema, users))

    db = txaioetcd.Database(etcd)

    async with db.begin(write=True) as txn:
        for i in range(10):
            name = 'user{}'.format(i)
            key = await idx1[txn, name]
            if key:
                user = await users[txn, key]
                if not user:
                    raise Exception('database index corrupt (data record for index entry missing)')
                print('user object already exists for name {}: {}'.format(name, key))
            else:
                user = User.create_test_user()
                user.name = name
                user.oid = uuid.uuid4()
                users[txn, user.oid] = user
                print('new user object stored for name {}: {}'.format(name, user.oid))

    async with db.begin(write=True) as txn:
        for k in range(5):
            i = random.randint(0, 9)
            name = 'user{}'.format(i)
            try:
                key = await idx1[txn, name]
            except IndexError:
                print('no user object for key {}'.format(key))
            else:
                del users[txn, key]
                print('user object deleted for key {}'.format(key))


# a wrapper that calls ensureDeferred
# see: https://meejah.ca/blog/python3-twisted-and-asyncio
def _main():
    return react(
        lambda reactor: ensureDeferred(
            main(reactor)
        )
    )


if __name__ == '__main__':
    txaio.start_logging(level='info')
    _main()
