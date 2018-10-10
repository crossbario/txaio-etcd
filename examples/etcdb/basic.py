import random

import txaio
txaio.use_twisted()

from twisted.internet.task import react
from twisted.internet.defer import ensureDeferred

from txaioetcd import Client, Database, MapUuidCbor

from user import User


async def main(reactor):

    tab_users = MapUuidCbor(1, marshal=lambda user: user.marshal(), unmarshal=User.parse)

    db = Database(Client(reactor))
    revision = await db.status()
    print('connected to etcd: revision', revision)

    user_oids = []

    # insert a couple of object in one etcd transaction
    async with db.begin(write=True) as txn:
        for i in range(10):
            user = User.create_test_user(name='user{}'.format(i))

            # INSERT: here we queue a key-value put operation with a native Python object
            tab_users[txn, user.oid] = user

            user_oids.append(user.oid)
            print('new user object stored: name={}, oid={}'.format(user.name, user.oid))

    async with db.begin(write=True) as txn:
        for oid in random.sample(user_oids, 5):

            # DELETE
            # tab_users.__delitem__((txn, oid))
            # await tab_users.delete((txn, oid))
            del tab_users[txn, oid]

            print('user object deleted for oid={}'.format(oid))

    async with db.begin() as txn:
        for oid in user_oids:
            # here we (directly/synchronously) get the value for a key as a native Python object
            user = await tab_users[txn, oid]
            if user:
                print('user object loaded: name={}, oid={}'.format(user.name, user.oid))
            else:
                print('no user object for oid={}'.format(oid))

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
