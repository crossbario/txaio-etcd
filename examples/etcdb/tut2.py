import random
import uuid

import txaio
txaio.use_twisted()

from twisted.internet.task import react
from twisted.internet.defer import ensureDeferred, inlineCallbacks

from txaioetcd import Client, Database
from txaioetcd import _pmap as pmap

from user import User


async def main(reactor):

    tab_users = pmap.MapUuidCbor(1, marshal=lambda user: user.marshal(), unmarshal=User.parse)

    db = Database(Client(reactor))
    revision = await db.status()
    print('connected to etcd: revision', revision)

    oid = uuid.uuid4()

    # store a native object in a UUID->CBOR table slot
    async with db.begin(write=True) as txn:
        user = User.create_test_user()
        user.oid = oid

        # the following enqueues the operation for when the transaction goes out of scope
        tab_users[txn, user.oid] = user

    print('new user object stored: name={}, oid={}'.format(user.name, user.oid))

    # load a native object from above UUID-CBOR table slot
    async with db.begin() as txn:
        user = await tab_users[txn, oid]
        if user:
            print('user object loaded: name={}, oid={}:\n{}'.format(user.name, user.oid, user))
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
