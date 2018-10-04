import random

import txaio
txaio.use_twisted()

from twisted.internet.task import react
from twisted.internet.defer import ensureDeferred, inlineCallbacks

from txaioetcd import Client, Database
from txaioetcd import _pmap as pmap

from user import User


async def main(reactor):

    tab_users = pmap.MapUuidCbor(1, marshal=lambda user: user.marshal(), unmarshal=User.parse)

    idx_users_by_name = pmap.MapStringUuid(2)
    tab_users.attach_index('idx1', lambda user: user.name, idx_users_by_name)

    idx_users_by_email = pmap.MapStringUuid(3)
    tab_users.attach_index('idx2', lambda user: user.email, idx_users_by_email)

    db = Database(Client(reactor))
    revision = await db.status()
    print('connected to etcd: revision', revision)

    users = []
    removed = set()

    async with db.begin(write=True) as txn:
        for i in range(10):
            user = User.create_test_user(name='user{}'.format(i))
            tab_users[txn, user.oid] = user
            users.append(user)
            print('new user object stored: name={}, oid={}'.format(user.name, user.oid))

    async with db.begin() as txn:
        for user in users:
            _user = await tab_users[txn, user.oid]
            assert _user

            user_oid = await idx_users_by_name[txn, user.name]
            assert user_oid == user.oid

            user_oid = await idx_users_by_email[txn, user.email]
            assert user_oid == user.oid
        print('index lookups successful')

    async with db.begin(write=True) as txn:
        for user in random.sample(users, 5):

            # DELETE
            # tab_users.__delitem__((txn, user.oid))
            # del tab_users[txn, user.oid]
            await tab_users.delete((txn, user.oid))

            print('user object deleted for oid={}'.format(user.oid))
            removed.add(user.oid)

    async with db.begin() as txn:
        for user in users:
            _user = await tab_users[txn, user.oid]
            if user.oid in removed:
                assert _user is None

                user_oid = await idx_users_by_name[txn, user.name]
                assert user_oid is None

                user_oid = await idx_users_by_email[txn, user.email]
                assert user_oid is None
            else:
                assert _user
                assert _user == user

                user_oid = await idx_users_by_name[txn, user.name]
                assert user_oid == user.oid

                user_oid = await idx_users_by_email[txn, user.email]
                assert user_oid == user.oid

            print('database structure for user oid={} verified successfully'.format(user.oid))

    print('etcd stats', db.stats())


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
