import uuid

import txaio
txaio.use_twisted()

from twisted.internet.task import react
from twisted.internet.defer import ensureDeferred

from txaioetcd import ClientPg, Database, pmap

from user import User


async def main(reactor):

    # Our main (asynchronous) entry point.

    # users table schema (a table with UUID keys and CBOR values holding User objects)
    tab_users = pmap.MapUuidCbor(1, marshal=lambda user: user.marshal(), unmarshal=User.parse)


    # persistent KV database client using PostgreSQL backend
    client = ClientPg(reactor)
    db = Database(client)
    revision = await db.status()
    print('connected to PostgreSQL-etcd: revision', revision)

    # new user ID
    oid = uuid.uuid4()

    # 1) store a native object in a UUID->CBOR table slot
    async with db.begin(write=True) as txn:
        user = User.create_test_user()
        user.oid = oid

        # the following enqueues the operation for when the transaction goes out of scope
        tab_users[txn, user.oid] = user

    print('new user object stored: name={}, oid={}'.format(user.name, user.oid))

    # 2) load a native object from above table slot
    async with db.begin() as txn:
        _user = await tab_users[txn, oid]

    assert user
    assert user == _user
    print('user object loaded: name={}, oid={}:\n{}'.format(_user.name, _user.oid, _user))

    # 3) delete an object from above table slot
    async with db.begin(write=True) as txn:
        del tab_users[txn, oid]

    print('user object deleted: oid={}'.format(oid))

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
