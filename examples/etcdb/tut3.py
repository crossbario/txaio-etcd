import random

import txaio
txaio.use_twisted()

from twisted.internet.task import react
from twisted.internet.defer import ensureDeferred

from txaioetcd import Client, Database

from user import User


async def main(reactor):
    # our main (asynchronous) entry point ..

    # persistent KV database client using etcd backend
    etcd = Client(reactor)
    db = Database(etcd)
    revision = await db.status()
    print('connected to etcd at revision {}'.format(revision))

    # users table
    users = await db.attach_slot(User.UUID, User.PMAP, create=True,
                                 marshal=User.marshal, unmarshal=User.parse,
                                 name=User.NAME, description=User.DESC)

    users_by_name = await db.attach_slot(User.UUID_IDX_BY_NAME, User.PMAP_IDX_BY_NAME, create=True)
    users.attach_index('idx1', lambda user: user.name, users_by_name)

    # select existing users
    async with db.begin() as txn:
        _users = await users.select(txn)
        if _users:
            print('yay, got {} users =)'.format(len(_users)))

            name = _users[0].name
            print('get user for name {}'.format(name))
            oid = await users_by_name[txn, name]
            if oid:
                user = await users[txn, oid]
                print('user: {}'.format(user))
        else:
            print('no users yet in database =(')

    # delete user objects
    oids = []
    async with db.begin(write=True) as txn:
        for i in range(5):
            name = 'user{}'.format(random.randint(1, 10))
            oid = await users_by_name[txn, name]
            if oid:
                print('deleting record')
                #del users[txn, oid]
                await users.delete((txn, oid))
                oids.append(oid)
                break
            else:
                print('missing data record!')

    print('user objects deleted: oids={}'.format(oids))

    # create and store new users
    oids = []
    async with db.begin(write=True) as txn:
        for i in range(1, 10):
            user = User.create_test_user(name='user{}'.format(i))
            user_exists = await users_by_name[txn, user.name]
            if True or not user_exists:
                users[txn, user.oid] = user
                oids.append(user.oid)
            else:
                print(user_exists)

    print('new user objects stored: oids={}'.format(oids))

    print('etcd stats', db.stats())



def _main():
    # a wrapper that calls ensureDeferred
    # see: https://meejah.ca/blog/python3-twisted-and-asyncio

    return react(
        lambda reactor: ensureDeferred(
            # call our real main ..
            main(reactor)
        )
    )


if __name__ == '__main__':
    # start logging at log level "info"
    txaio.start_logging(level='info')

    # run our main function ..
    _main()
