import uuid

import txaio
txaio.use_twisted()

from twisted.internet.task import react
from twisted.internet.defer import ensureDeferred

from txaioetcd import Client, Database, pmap

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

    async with db.begin() as txn:
        _user_keys, _users = await users.select(txn, return_keys=True, return_values=True)
        if _users:
            print('got {} users'.format(len(_users)))
            if False:
                for user in _users:
                    print('loaded user\n{}'.format(user))
        else:
            print('no users yet in database')

    # new user ID
    oid = uuid.uuid4()

    # 1) store a native object in a UUID->CBOR table slot
    async with db.begin(write=True) as txn:
        user = User.create_test_user()
        user.oid = oid

        # the following enqueues the operation for when the transaction goes out of scope
        users[txn, user.oid] = user

    print('new user object stored: name={}, oid={}'.format(user.name, user.oid))

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
